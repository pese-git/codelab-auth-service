"""Refresh Token service for token rotation"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import logger
from app.models.refresh_token import RefreshToken
from app.schemas.token import RefreshTokenPayload
from app.utils.crypto import hash_token_jti


class RefreshTokenService:
    """Service for refresh token management and rotation"""

    async def save_refresh_token(
        self,
        db: AsyncSession,
        payload: RefreshTokenPayload,
        parent_jti: str | None = None,
        session_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> RefreshToken:
        """
        Save refresh token to database
        
        Args:
            db: Database session
            payload: Refresh token payload
            parent_jti: Parent token JTI (for rotation chain)
            session_id: Session identifier (for multi-device support)
            ip_address: Client IP address
            user_agent: Client User-Agent
            
        Returns:
            Created RefreshToken record
        """
        # Hash JTI
        jti_hash = hash_token_jti(payload.jti)
        parent_jti_hash = hash_token_jti(parent_jti) if parent_jti else None
        
        # Generate session_id if not provided
        if not session_id:
            session_id = str(uuid.uuid4())

        # Create refresh token record
        refresh_token = RefreshToken(
            jti_hash=jti_hash,
            user_id=payload.sub,
            client_id=payload.client_id,
            scope=payload.scope,
            expires_at=datetime.fromtimestamp(payload.exp, tz=timezone.utc),
            parent_jti_hash=parent_jti_hash,
            session_id=session_id,
            last_used=datetime.now(timezone.utc),
            last_rotated_at=datetime.now(timezone.utc),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        db.add(refresh_token)
        await db.commit()
        await db.refresh(refresh_token)

        logger.debug(f"Refresh token saved: {jti_hash[:16]}..., session_id={session_id}")

        return refresh_token

    async def get_by_jti(
        self,
        db: AsyncSession,
        jti: str,
    ) -> RefreshToken | None:
        """
        Get refresh token by JTI
        
        Args:
            db: Database session
            jti: JWT ID
            
        Returns:
            RefreshToken or None if not found
        """
        jti_hash = hash_token_jti(jti)

        result = await db.execute(
            select(RefreshToken).where(RefreshToken.jti_hash == jti_hash)
        )
        return result.scalar_one_or_none()

    async def validate_refresh_token(
        self,
        db: AsyncSession,
        jti: str,
    ) -> tuple[bool, str | None]:
        """
        Validate refresh token
        
        Args:
            db: Database session
            jti: JWT ID
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        token = await self.get_by_jti(db, jti)

        if not token:
            return False, "Refresh token not found"

        if token.revoked:
            # SECURITY: Refresh token reuse detected!
            logger.warning(
                f"SECURITY: Refresh token reuse detected! "
                f"jti={jti[:16]}..., user_id={token.user_id}"
            )
            # Revoke all tokens in the chain
            await self.revoke_token_chain(db, token)
            return False, "Refresh token has been revoked (reuse detected)"

        if token.is_expired:
            return False, "Refresh token has expired"

        return True, None

    async def revoke_token(
        self,
        db: AsyncSession,
        jti: str,
    ) -> bool:
        """
        Revoke a refresh token
        
        Args:
            db: Database session
            jti: JWT ID
            
        Returns:
            True if revoked, False if not found
        """
        token = await self.get_by_jti(db, jti)
        if not token:
            return False

        token.revoked = True
        token.revoked_at = datetime.now(timezone.utc)

        await db.commit()

        logger.info(f"Refresh token revoked: {jti[:16]}...")

        return True

    async def revoke_token_chain(
        self,
        db: AsyncSession,
        token: RefreshToken,
    ) -> None:
        """
        Revoke entire token chain (for security incidents)
        
        Args:
            db: Database session
            token: RefreshToken that was reused
        """
        # Revoke the token itself
        token.revoked = True
        token.revoked_at = datetime.now(timezone.utc)

        # Find and revoke all tokens in the chain
        # (tokens with same user_id and client_id)
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == token.user_id,
                RefreshToken.client_id == token.client_id,
                RefreshToken.revoked == False,
            )
        )
        tokens_to_revoke = result.scalars().all()

        for t in tokens_to_revoke:
            t.revoked = True
            t.revoked_at = datetime.now(timezone.utc)

        await db.commit()

        logger.warning(
            f"SECURITY: Revoked {len(tokens_to_revoke)} tokens in chain "
            f"for user {token.user_id}"
        )

    async def cleanup_expired_tokens(
        self,
        db: AsyncSession,
        days_to_keep: int = 7,
    ) -> int:
        """
        Delete expired refresh tokens older than specified days
        
        Args:
            db: Database session
            days_to_keep: Number of days to keep expired tokens
            
        Returns:
            Number of deleted tokens
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        result = await db.execute(
            select(RefreshToken).where(RefreshToken.expires_at < cutoff_date)
        )
        tokens_to_delete = result.scalars().all()

        for token in tokens_to_delete:
            await db.delete(token)

        await db.commit()

        count = len(tokens_to_delete)
        if count > 0:
            logger.info(f"Cleaned up {count} expired refresh tokens")

        return count

    async def revoke_session(
        self,
        db: AsyncSession,
        user_id: str,
        session_id: str,
    ) -> bool:
        """
        Revoke all tokens for a specific session
        
        Args:
            db: Database session
            user_id: User ID
            session_id: Session ID to revoke
            
        Returns:
            True if any tokens were revoked
        """
        result = await db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.session_id == session_id,
                    RefreshToken.revoked == False,
                )
            )
        )
        tokens = result.scalars().all()

        revoked_count = 0
        for token in tokens:
            token.revoked = True
            token.revoked_at = datetime.now(timezone.utc)
            revoked_count += 1

        if revoked_count > 0:
            await db.commit()
            logger.info(
                f"Revoked {revoked_count} tokens for session {session_id} "
                f"(user_id={user_id})"
            )

        return revoked_count > 0

    async def get_user_sessions(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> list[RefreshToken]:
        """
        Get all active sessions for a user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            List of active RefreshToken records (one per session)
        """
        # Get the latest token for each session
        result = await db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked == False,
                )
            )
        )
        
        all_tokens = result.scalars().all()
        
        # Group by session_id, keep the latest for each
        sessions_map = {}
        for token in all_tokens:
            if token.session_id not in sessions_map:
                sessions_map[token.session_id] = token
            elif token.created_at > sessions_map[token.session_id].created_at:
                sessions_map[token.session_id] = token
        
        return list(sessions_map.values())

    async def get_session_metadata(
        self,
        db: AsyncSession,
        user_id: str,
        session_id: str,
    ) -> dict | None:
        """
        Get metadata for a specific session
        
        Args:
            db: Database session
            user_id: User ID
            session_id: Session ID
            
        Returns:
            Session metadata dict or None if not found
        """
        result = await db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.session_id == session_id,
                    RefreshToken.revoked == False,
                )
            )
        )
        
        token = result.scalars().first()
        if not token:
            return None
        
        return {
            "session_id": token.session_id,
            "client_id": token.client_id,
            "created_at": token.created_at,
            "last_used": token.last_used,
            "last_rotated_at": token.last_rotated_at,
            "ip_address": token.ip_address,
            "user_agent": token.user_agent,
            "expires_at": token.expires_at,
        }


# Global instance
refresh_token_service = RefreshTokenService()
