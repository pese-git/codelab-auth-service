"""Email service for sending confirmation emails"""

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import logger, settings
from app.models.email_confirmation_token import EmailConfirmationToken
from app.models.user import User


class EmailService:
    """Service for email operations"""

    async def generate_confirmation_token(
        self,
        user_id: str,
        db: AsyncSession | None = None,
        expires_in_hours: int = 24,
    ) -> str:
        """
        Generate a secure confirmation token for email verification.
        
        Args:
            user_id: User ID to generate token for
            db: Database session (optional, for storing token)
            expires_in_hours: Token expiration time in hours (default: 24)
            
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

    async def save_confirmation_token(
        self,
        user_id: str,
        token: str,
        db: AsyncSession,
        expires_in_hours: int = 24,
        commit: bool = True,
    ) -> bool:
        """
        Save confirmation token to database.
        
        Args:
            user_id: User ID
            token: Confirmation token
            db: Database session
            expires_in_hours: Token expiration time in hours (default: 24)
            commit: Whether to commit the transaction (default: True)
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Calculate expiration time
            expires_at = datetime.now(UTC) + timedelta(hours=expires_in_hours)
            
            # Create token record
            token_record = EmailConfirmationToken(
                user_id=user_id,
                token=token,
                expires_at=expires_at,
            )
            
            # Save to database
            db.add(token_record)
            await db.flush()  # Flush to ensure the record is inserted
            
            if commit:
                await db.commit()  # Commit the transaction
            
            logger.info(
                f"Confirmation token saved for user {user_id}",
                extra={"user_id": user_id, "expires_at": expires_at},
            )
            
            return True
        except Exception as e:
            logger.error(
                f"Failed to save confirmation token for user {user_id}: {e}",
                extra={"user_id": user_id},
            )
            # Rollback on error
            try:
                await db.rollback()
            except Exception as rollback_err:
                logger.error(f"Failed to rollback: {rollback_err}")
            return False

    async def send_confirmation_email(
        self,
        user: User,
        token: str,
        db: AsyncSession | None = None,
    ) -> bool:
        """Send email confirmation message using EmailNotificationService

        Args:
            user: User object
            token: Email confirmation token
            db: Database session for storing token

        Returns:
            True if email sent/queued successfully, False otherwise
        """
        try:
            # Import here to avoid circular imports
            from app.services.audit_service import audit_service
            from app.services.email_notifications import EmailNotificationService

            # Create notification service
            notification_service = EmailNotificationService()

            # Send confirmation email (async, queued as background task)
            success = await notification_service.send_confirmation_email(
                user, token, background=True
            )

            # Log to audit (if db session is available)
            if db and success:
                try:
                    await audit_service.log_email_sent(
                        db=db,
                        user_id=user.id,
                        template_name="confirmation",
                        recipient=user.email,
                    )
                except Exception as audit_err:
                    logger.warning(
                        f"Failed to log confirmation email to audit: {audit_err}",
                        extra={"user_id": user.id},
                    )

            if success:
                logger.info(
                    f"Confirmation email sent/queued for {user.email}",
                    extra={"user_id": user.id, "email": user.email},
                )
            else:
                logger.warning(
                    f"Failed to send confirmation email to {user.email}",
                    extra={"user_id": user.id, "email": user.email},
                )
                # Log failure to audit (if db session is available)
                if db:
                    try:
                        await audit_service.log_email_failed(
                            db=db,
                            user_id=user.id,
                            template_name="confirmation",
                            error="Failed to send confirmation email",
                        )
                    except Exception as audit_err:
                        logger.warning(
                            f"Failed to log email failure to audit: {audit_err}",
                            extra={"user_id": user.id},
                        )

            return success

        except Exception as e:
            logger.error(
                f"Error sending confirmation email to {user.email}: {e}",
                extra={"user_id": user.id, "email": user.email},
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
    ) -> User | None:
        """Verify an email confirmation token and return associated user

        Args:
            db: Database session
            token: Token to verify

        Returns:
            User object if token is valid and not expired, None otherwise
        """
        try:
            from app.services.audit_service import audit_service
            
            # Query for the token
            result = await db.execute(
                select(EmailConfirmationToken).where(
                    EmailConfirmationToken.token == token
                )
            )
            token_record = result.scalars().first()

            if not token_record:
                logger.warning("Token not found in database")
                # Log token verification failure to audit
                try:
                    await audit_service.log_email_confirmation_failed(
                        db=db,
                        reason="token_not_found",
                    )
                except Exception as audit_err:
                    logger.warning(f"Failed to log token failure to audit: {audit_err}")
                return None

            # Check if token has expired
            now = datetime.now(UTC)
            if token_record.expires_at < now:
                logger.warning(
                    f"Token expired at {token_record.expires_at}",
                    extra={"user_id": token_record.user_id},
                )
                # Log token expiration to audit
                try:
                    await audit_service.log_email_confirmation_failed(
                        db=db,
                        reason="token_expired",
                    )
                except Exception as audit_err:
                    logger.warning(f"Failed to log token expiration to audit: {audit_err}")
                return None

            # Get user by user_id
            from app.models.user import User

            result = await db.execute(
                select(User).where(User.id == token_record.user_id)
            )
            user = result.scalars().first()

            if not user:
                logger.error(
                    "User not found for token",
                    extra={"user_id": token_record.user_id},
                )
                # Log user not found to audit
                try:
                    await audit_service.log_email_confirmation_failed(
                        db=db,
                        reason="user_not_found",
                    )
                except Exception as audit_err:
                    logger.warning(f"Failed to log user not found to audit: {audit_err}")
                return None

            logger.info(
                f"Token verified successfully for user {user.username}",
                extra={"user_id": user.id},
            )
            
            # Log successful token verification to audit
            try:
                await audit_service.log_email_confirmation_token_generated(
                    db=db,
                    user_id=user.id,
                )
            except Exception as audit_err:
                logger.warning(f"Failed to log token verification to audit: {audit_err}")

            return user

        except Exception as e:
            logger.error(f"Error verifying confirmation token: {e}")
            return None


# Global instance
email_service = EmailService()
