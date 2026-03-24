"""Password reset endpoints"""

import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.config import logger, settings
from app.schemas.password_reset import (
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordResetResponse,
)
from app.services.password_reset_service import PasswordResetService
from app.services.user_service import user_service
from app.services.email_notifications import EmailNotificationService
from app.services.rate_limiter import rate_limiter
from app.services.brute_force_protection import BruteForceProtection
from app.services.audit_service import audit_service
from app.utils.validators import validate_password
from app.utils.crypto import hash_password

router = APIRouter(prefix="/api/v1", tags=["Password Reset"])

# Initialize services
password_reset_service = PasswordResetService()
brute_force_protection = BruteForceProtection()
email_notification_service = EmailNotificationService()


@router.post(
    "/auth/password-reset/request",
    response_model=PasswordResetResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Password reset instructions sent if email exists"},
        429: {"description": "Too many reset requests from this email/IP"},
        422: {"description": "Invalid email format"},
    },
)
async def request_password_reset(
    request: Request,
    data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> PasswordResetResponse:
    """
    Request a password reset.

    - **email**: Valid email address

    Returns:
        - 200 OK: Email sent (or account doesn't exist, but we don't reveal that)
        - 429 Too Many Requests: Rate limit exceeded
        - 422 Unprocessable Entity: Invalid input
    """
    client_ip = request.client.host if request.client else "unknown"

    try:
        # Rate limiting by email
        is_allowed, remaining = await rate_limiter.check_rate_limit_username(
            username=data.email,
            limit=settings.password_reset_request_limit,
            window=3600,  # 1 hour
        )

        if not is_allowed:
            logger.warning(
                f"Password reset rate limit exceeded for email {data.email}",
                extra={"email_hash": data.email, "client_ip": client_ip},
            )

            await audit_service.log(
                db=db,
                event_type="PASSWORD_RESET_RATE_LIMIT_EXCEEDED",
                user_id=None,
                details={
                    "email": data.email,
                    "client_ip": client_ip,
                },
            )

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many password reset requests. Try again later.",
            )

        # Find user by email (don't reveal if user exists)
        user = await user_service.get_by_email(db, data.email)

        # Create token and send email only if user exists
        if user:
            try:
                # Create reset token
                token = await password_reset_service.create_token(db, user.id)

                # Log the request
                await audit_service.log(
                    db=db,
                    event_type="PASSWORD_RESET_REQUESTED",
                    user_id=user.id,
                    details={
                        "email": user.email,
                        "client_ip": client_ip,
                    },
                )

                # Send email asynchronously
                asyncio.create_task(
                    email_notification_service.send_password_reset_email(
                        user, token
                    )
                )

                logger.info(
                    f"Password reset requested for user {user.id}",
                    extra={"user_id": user.id, "client_ip": client_ip},
                )
            except Exception as e:
                logger.error(
                    f"Error creating password reset token for user {user.id}: {e}",
                    extra={"user_id": user.id},
                )
                # Don't fail the request even if email sending fails
        else:
            # User doesn't exist - log for security monitoring but return same response
            logger.info(
                f"Password reset requested for non-existent email: {data.email}",
                extra={"email_hash": data.email, "client_ip": client_ip},
            )

        # Always return same response for security (don't reveal if user exists)
        return PasswordResetResponse(
            message="If an account with that email exists, you will receive password reset instructions."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in password reset request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post(
    "/auth/password-reset/confirm",
    response_model=PasswordResetResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Password successfully reset"},
        400: {"description": "Invalid token or password"},
        429: {"description": "Too many reset attempts"},
        422: {"description": "Invalid input data"},
    },
)
async def confirm_password_reset(
    request: Request,
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
) -> PasswordResetResponse:
    """
    Confirm password reset with token.

    - **token**: Password reset token from email
    - **password**: New password (8-72 characters)
    - **password_confirm**: Password confirmation (must match password)

    Returns:
        - 200 OK: Password successfully reset
        - 400 Bad Request: Invalid token or password
        - 429 Too Many Requests: Too many failed attempts
        - 422 Unprocessable Entity: Invalid input
    """
    client_ip = request.client.host if request.client else "unknown"

    try:
        # Validate password confirmation
        is_valid, error_msg = data.validate()
        if not is_valid:
            logger.warning(
                f"Password reset password mismatch from {client_ip}",
                extra={"client_ip": client_ip},
            )

            await audit_service.log(
                db=db,
                event_type="PASSWORD_RESET_VALIDATION_FAILED",
                user_id=None,
                details={
                    "reason": "passwords_mismatch",
                    "client_ip": client_ip,
                },
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg or "Invalid request",
            )

        # Validate password strength
        is_valid, error_msg = validate_password(data.password)
        if not is_valid:
            logger.warning(
                f"Password reset weak password from {client_ip}",
                extra={"client_ip": client_ip},
            )

            await audit_service.log(
                db=db,
                event_type="PASSWORD_RESET_VALIDATION_FAILED",
                user_id=None,
                details={
                    "reason": "weak_password",
                    "client_ip": client_ip,
                },
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg or "Password does not meet requirements",
            )

        # Check brute force protection
        is_locked, lockout_msg = await brute_force_protection.is_locked_out(
            username="password_reset",
            ip_address=client_ip,
        )

        if is_locked:
            logger.warning(
                f"Password reset brute force protection triggered from {client_ip}",
                extra={"client_ip": client_ip},
            )

            await audit_service.log(
                db=db,
                event_type="PASSWORD_RESET_BRUTE_FORCE_DETECTED",
                user_id=None,
                details={"client_ip": client_ip},
            )

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=lockout_msg or "Too many reset attempts",
            )

        # Verify token
        user_id = await password_reset_service.verify_token(db, data.token)

        if not user_id:
            # Log failed attempt
            await brute_force_protection.record_failed_attempt(
                username="password_reset",
                ip_address=client_ip,
            )

            logger.warning(
                f"Password reset invalid token from {client_ip}",
                extra={"client_ip": client_ip},
            )

            await audit_service.log(
                db=db,
                event_type="PASSWORD_RESET_INVALID_TOKEN",
                user_id=None,
                details={
                    "reason": "invalid_or_expired_token",
                    "client_ip": client_ip,
                },
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset token",
            )

        # Get user
        user = await user_service.get_by_id(db, user_id)
        if not user:
            logger.warning(f"User not found for password reset: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset token",
            )

        try:
            # Update password
            user.password_hash = hash_password(data.password)
            db.add(user)
            await db.commit()
            await db.refresh(user)

            # Mark token as used
            await password_reset_service.mark_token_used(db, data.token)

            # Reset brute force counter
            await brute_force_protection.reset_failed_attempts(
                username="password_reset",
                ip_address=client_ip,
            )

            # Log successful password reset
            await audit_service.log(
                db=db,
                event_type="PASSWORD_RESET_SUCCESS",
                user_id=user.id,
                details={
                    "username": user.username,
                    "client_ip": client_ip,
                },
            )

            logger.info(
                f"Password reset successful for user {user.id}",
                extra={"user_id": user.id, "client_ip": client_ip},
            )

            return PasswordResetResponse(message="Password successfully reset")

        except Exception as e:
            logger.error(f"Error updating password for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in password reset confirm: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
