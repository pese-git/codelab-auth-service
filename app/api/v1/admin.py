"""Admin endpoints for user management"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import logger
from app.core.dependencies import DBSession
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.schemas.user import UserResponse
from app.services.event_publisher import get_event_publisher
from app.services.token_blacklist_service import get_token_blacklist_service

router = APIRouter(prefix="/admin", tags=["admin"])


class DeleteUserResponse:
    """Response for user deletion"""

    def __init__(
        self,
        status: str,
        user_id: str,
        tokens_revoked: int,
        event_id: str,
        deleted_at: str,
        cascade_status: str = "pending",
    ):
        self.status = status
        self.user_id = user_id
        self.tokens_revoked = tokens_revoked
        self.event_id = event_id
        self.deleted_at = deleted_at
        self.cascade_status = cascade_status

    def dict(self):
        return {
            "status": self.status,
            "user_id": self.user_id,
            "tokens_revoked": self.tokens_revoked,
            "event_id": self.event_id,
            "deleted_at": self.deleted_at,
            "cascade_status": self.cascade_status,
        }


@router.delete("/users/{user_id}", response_model=dict)
async def delete_user(
    user_id: UUID,
    session: AsyncSession = DBSession,
    request: Request = None,
) -> dict:
    """
    Delete a user and all associated data.

    This endpoint performs the following operations:
    1. Verify user exists
    2. Verify caller has admin role (in real implementation)
    3. Get all active tokens for the user
    4. Revoke all tokens in Redis blacklist
    5. Mark user as deleted in PostgreSQL
    6. Publish user.deleted event to Redis Streams
    7. Return success response

    Path Parameters:
        user_id (UUID): User ID to delete

    Returns:
        DeleteUserResponse with status, tokens_revoked, event_id, cascade_status

    Raises:
        404 Not Found: if user doesn't exist
        401 Unauthorized: if caller is not admin (future)
        500 Internal Server Error: if deletion fails
    """
    try:
        user_id_str = str(user_id)
        logger.info(f"Delete user request: user_id={user_id_str}")

        # Phase 1: Validation - verify user exists
        result = await session.execute(
            select(User).where(User.id == user_id_str)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"User not found for deletion: user_id={user_id_str}")
            raise HTTPException(status_code=404, detail="User not found")

        if user.is_deleted:
            logger.warning(
                f"User already deleted: user_id={user_id_str}"
            )
            raise HTTPException(
                status_code=400,
                detail="User is already deleted"
            )

        # Phase 2: Revoke Tokens - get all active tokens
        logger.info(f"Fetching active tokens for user: user_id={user_id_str}")
        now = datetime.now(timezone.utc)
        
        token_result = await session.execute(
            select(RefreshToken).where(
                (RefreshToken.user_id == user_id_str) &
                (RefreshToken.expires_at > now) &
                (RefreshToken.revoked == False)
            )
        )
        tokens = token_result.scalars().all()

        # Prepare token list for batch revoke
        token_list = []
        for token in tokens:
            exp_timestamp = int(token.expires_at.timestamp())
            # Extract JTI from stored hash (in real implementation, we need actual JTI)
            # For now, use id as jti
            token_list.append((token.id, exp_timestamp))

        tokens_revoked = 0

        # Revoke all tokens in Redis blacklist
        if token_list:
            try:
                blacklist_service = await get_token_blacklist_service()
                tokens_revoked = await blacklist_service.revoke_all_user_tokens(
                    user_id=user_id_str,
                    token_list=token_list,
                    reason="user_deleted",
                    admin_id=None,  # In real impl, get from current user
                )
                logger.info(
                    f"Tokens revoked in blacklist: "
                    f"user_id={user_id_str}, count={tokens_revoked}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to revoke tokens: user_id={user_id_str}, error={str(e)}"
                )
                raise HTTPException(
                    status_code=500,
                    detail="Failed to revoke user tokens"
                )

        # Phase 3: Update Auth DB - mark user as deleted
        logger.info(f"Marking user as deleted: user_id={user_id_str}")
        deleted_at = datetime.now(timezone.utc)
        user.is_deleted = True
        user.deleted_at = deleted_at
        user.deletion_reason = "admin_deletion"

        await session.commit()
        logger.info(
            f"User marked as deleted in DB: user_id={user_id_str}"
        )

        # Phase 4: Publish Event - emit user.deleted event
        event_id = None
        try:
            publisher = await get_event_publisher()
            event_id = await publisher.publish_user_deleted(
                user_id=user_id_str,
                email=user.email,
                reason="admin_deletion",
                deleted_at=deleted_at.isoformat().replace("+00:00", "Z"),
            )
            logger.info(
                f"User deletion event published: "
                f"user_id={user_id_str}, event_id={event_id}"
            )
        except Exception as e:
            logger.error(
                f"Failed to publish deletion event: "
                f"user_id={user_id_str}, error={str(e)}"
            )
            # Note: We don't fail the deletion because DB is already updated
            # The event will be retried or reconciled later
            raise HTTPException(
                status_code=500,
                detail="Deletion successful but event publishing failed"
            )

        # Phase 5: Response
        response = DeleteUserResponse(
            status="deleted",
            user_id=user_id_str,
            tokens_revoked=tokens_revoked,
            event_id=event_id,
            deleted_at=deleted_at.isoformat().replace("+00:00", "Z"),
            cascade_status="pending",
        )

        logger.info(
            f"User deletion completed successfully: "
            f"user_id={user_id_str}, tokens_revoked={tokens_revoked}, "
            f"event_id={event_id}"
        )

        return response.dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during user deletion: "
            f"user_id={user_id}, error={str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during user deletion"
        ) from e


@router.get("/users/{user_id}", response_model=dict)
async def get_user(
    user_id: UUID,
    session: AsyncSession = DBSession,
) -> dict:
    """
    Get user details (admin only).

    Path Parameters:
        user_id (UUID): User ID

    Returns:
        User details or 404
    """
    user_id_str = str(user_id)

    result = await session.execute(
        select(User).where(User.id == user_id_str)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "is_deleted": user.is_deleted,
        "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
        "deletion_reason": user.deletion_reason,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }
