"""Password reset service"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import logger
from app.models.password_reset_token import PasswordResetToken
from app.utils.crypto import constant_time_compare, hash_password

# Token expiration time in minutes
TOKEN_EXPIRATION_MINUTES = 30


class PasswordResetService:
    """Service for password reset operations"""

    async def create_token(self, db: AsyncSession, user_id: str) -> str:
        """
        Create a new password reset token
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Plain text token (only shown once to user)
            
        Raises:
            ValueError: If user not found or other validation error
        """
        # Generate cryptographically secure token
        token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(token)

        # Set expiration time
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=TOKEN_EXPIRATION_MINUTES)

        # Create token record
        reset_token = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            created_at=now,
            expires_at=expires_at,
        )

        db.add(reset_token)
        await db.commit()

        logger.info(f"Password reset token created for user {user_id}")

        return token

    async def verify_token(self, db: AsyncSession, token: str) -> str | None:
        """
        Verify a password reset token
        
        Args:
            db: Database session
            token: Plain text token to verify
            
        Returns:
            User ID if token is valid, None otherwise
        """
        if not token:
            return None

        # Hash the token
        token_hash = self._hash_token(token)

        # Query for token
        result = await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash
            )
        )
        reset_token = result.scalar_one_or_none()

        if not reset_token:
            logger.warning("Password reset attempt with invalid token")
            return None

        # Check if expired
        if reset_token.is_expired():
            logger.warning(f"Password reset attempt with expired token for user {reset_token.user_id}")
            return None

        # Check if already used
        if reset_token.is_used():
            logger.warning(f"Password reset attempt with already used token for user {reset_token.user_id}")
            return None

        return reset_token.user_id

    async def mark_token_used(self, db: AsyncSession, token: str) -> bool:
        """
        Mark a password reset token as used
        
        Args:
            db: Database session
            token: Plain text token to mark as used
            
        Returns:
            True if successful, False otherwise
        """
        if not token:
            return False

        # Hash the token
        token_hash = self._hash_token(token)

        # Query for token
        result = await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash
            )
        )
        reset_token = result.scalar_one_or_none()

        if not reset_token:
            return False

        # Mark as used
        reset_token.used_at = datetime.now(timezone.utc)
        await db.commit()

        logger.info(f"Password reset token marked as used for user {reset_token.user_id}")

        return True

    async def cleanup_expired_tokens(self, db: AsyncSession) -> int:
        """
        Delete expired password reset tokens
        
        Args:
            db: Database session
            
        Returns:
            Number of tokens deleted
        """
        now = datetime.now(timezone.utc)

        # Delete all expired tokens
        result = await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.expires_at < now
            )
        )
        tokens = result.scalars().all()

        deleted_count = len(tokens)

        for token in tokens:
            await db.delete(token)

        await db.commit()

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired password reset tokens")

        return deleted_count

    @staticmethod
    def _hash_token(token: str) -> str:
        """
        Hash a token using SHA-256
        
        Args:
            token: Plain text token
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(token.encode()).hexdigest()
