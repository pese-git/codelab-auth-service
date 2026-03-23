"""Email service for sending confirmation emails"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, ForeignKey, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import logger, settings
from app.models.database import Base


class EmailConfirmationToken(Base):
    """Model for email confirmation tokens"""

    __tablename__ = "email_confirmation_tokens"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Token
    token: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    # Expiration timestamp
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Creation timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class EmailService:
    """Service for email operations"""

    async def generate_confirmation_token(
        self,
        user_id: str,
        db: AsyncSession | None = None,
    ) -> str:
        """
        Generate a secure confirmation token for email verification.
        
        Args:
            user_id: User ID to generate token for
            db: Database session (optional, for storing token)
            
        Returns:
            Generated token string
        """
        # Generate secure random token (32 bytes = 256 bits)
        token = secrets.token_urlsafe(32)
        
        logger.debug(
            f"Generated email confirmation token for user {user_id}",
            extra={"user_id": user_id, "token_length": len(token)},
        )
        
        return token

    async def send_confirmation_email(
        self,
        email: str,
        username: str,
        confirmation_token: str,
        confirmation_url: str | None = None,
    ) -> bool:
        """
        Send email confirmation message.
        
        Args:
            email: Recipient email address
            username: Username for personalization
            confirmation_token: Token for email verification
            confirmation_url: Full URL for confirmation (if None, URL will be constructed)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # For now, just log the confirmation email
            # In production, this would integrate with SMTP service
            if confirmation_url is None:
                confirmation_url = f"https://auth.codelab.local/confirm-email?token={confirmation_token}"
            
            logger.info(
                f"Email confirmation needed for {email}",
                extra={
                    "email": email,
                    "username": username,
                    "confirmation_url": confirmation_url,
                },
            )
            
            # TODO: Implement actual email sending via SMTP
            # Example structure:
            # smtp_client = aiosmtplib.SMTP(settings.smtp_host, settings.smtp_port)
            # await smtp_client.send_message(message)
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to send confirmation email to {email}: {e}",
                extra={"email": email, "error": str(e)},
            )
            return False

    def is_confirmation_required(self) -> bool:
        """
        Check if email confirmation is required by configuration.
        
        Returns:
            True if REQUIRE_EMAIL_CONFIRMATION is enabled
        """
        return settings.require_email_confirmation

    async def verify_confirmation_token(
        self,
        db: AsyncSession,
        token: str,
    ) -> str | None:
        """
        Verify an email confirmation token.
        
        Args:
            db: Database session
            token: Token to verify
            
        Returns:
            User ID if token is valid, None otherwise
        """
        # For now, just return a placeholder
        # In production, this would query the database for the token
        # and verify it hasn't expired
        
        logger.debug(f"Verifying confirmation token")
        
        # TODO: Implement token verification with database
        # 1. Query email_confirmation_tokens table for matching token
        # 2. Check if token has expired (expires_at > now)
        # 3. Return user_id if valid, None otherwise
        
        return None


# Global instance
email_service = EmailService()
