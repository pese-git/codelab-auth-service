"""Email notification service with template rendering, sending, and retry logic"""

import asyncio
import logging
from pathlib import Path

from app.core.config import settings
from app.models.user import User
from app.services.email_retry import EmailRetryService
from app.services.email_sender import SMTPEmailSender
from app.services.email_templates import EmailTemplateEngine

logger = logging.getLogger("auth-service")

# Lazy import to avoid circular dependency
_audit_service = None

def get_audit_service():
    """Get audit service (lazy import to avoid circular dependency)"""
    global _audit_service
    if _audit_service is None:
        from app.services.audit_service import audit_service as imported_audit_service
        _audit_service = imported_audit_service
    return _audit_service


class EmailNotificationService:
    """High-level service for sending email notifications with templates"""

    def __init__(
        self,
        template_engine: EmailTemplateEngine | None = None,
        sender: SMTPEmailSender | None = None,
        retry_service: EmailRetryService | None = None,
    ):
        """Initialize notification service with dependencies

        Args:
            template_engine: EmailTemplateEngine for rendering templates
            sender: SMTPEmailSender for sending emails
            retry_service: EmailRetryService for retry logic

        Example:
            >>> service = EmailNotificationService()
            >>> await service.send_welcome_email(user)
        """
        # Initialize template engine with email templates directory
        if template_engine is None:
            template_dir = Path(__file__).parent.parent / "templates" / "emails"
            template_engine = EmailTemplateEngine(template_dir)

        self.template_engine = template_engine
        self.sender = sender or SMTPEmailSender()
        self.retry_service = (
            retry_service or EmailRetryService(self.sender)
        )

    async def send_welcome_email(
        self, user: User, background: bool = True
    ) -> bool:
        """Send welcome email to newly registered user

        Args:
            user: User object with email and username
            background: If True, schedule as background task

        Returns:
            True if email sent/queued successfully

        Example:
            >>> success = await service.send_welcome_email(user)
        """
        if not settings.send_welcome_email:
            logger.debug(f"Welcome email disabled for {user.username}")
            return True

        if background:
            asyncio.create_task(
                self._send_welcome_email_internal(user)
            )
            return True

        return await self._send_welcome_email_internal(user)

    async def send_confirmation_email(
        self, user: User, token: str, background: bool = True
    ) -> bool:
        """Send email confirmation link to user

        Args:
            user: User object
            token: Email confirmation token
            background: If True, schedule as background task

        Returns:
            True if email sent/queued successfully

        Example:
            >>> success = await service.send_confirmation_email(user, token)
        """
        if not settings.require_email_confirmation:
            logger.debug(f"Email confirmation disabled for {user.username}")
            return True

        if background:
            asyncio.create_task(
                self._send_confirmation_email_internal(user, token)
            )
            return True

        return await self._send_confirmation_email_internal(user, token)

    async def send_password_reset_email(
        self, user: User, reset_token: str
    ) -> bool:
        """Send password reset link to user

        Args:
            user: User object
            reset_token: Password reset token

        Returns:
            True if email sent successfully

        Example:
            >>> success = await service.send_password_reset_email(user, token)
        """
        if not settings.send_password_reset_email:
            logger.debug(f"Password reset email disabled for {user.username}")
            return True

        return await self._send_password_reset_email_internal(
            user, reset_token
        )

    async def _send_welcome_email_internal(self, user: User) -> bool:
        """Internal method to send welcome email

        Args:
            user: User object

        Returns:
            True if email sent successfully
        """
        try:
            # Prepare context for template
            context = {
                "username": user.username,
                "email": user.email,
                "activation_link": (
                    f"https://codelab.local/activate?user_id={user.id}"
                ),
                "registration_date": user.created_at.isoformat()
                if user.created_at
                else "N/A",
                "to_email": user.email,
                "from_email": settings.smtp_from_email,
            }

            # Render template
            message = await self.template_engine.render_template(
                "welcome", context
            )

            # Send with retry
            success = await self.retry_service.send_with_retry(
                message, max_retries=settings.smtp_max_retries
            )

            if success:
                logger.info(f"Welcome email sent to {user.username}")
                # Log to audit asynchronously (don't block email sending)
                try:
                    audit_service = get_audit_service()
                    asyncio.create_task(
                        audit_service.log_email_sent(
                            db=None,  # No DB session in background task
                            user_id=user.id,
                            template_name="welcome",
                            recipient=user.email,
                        )
                    )
                except Exception as audit_err:
                    logger.warning(f"Failed to log email sent to audit: {audit_err}")
            else:
                logger.warning(f"Failed to send welcome email to {user.username}")
                # Log failure to audit
                try:
                    audit_service = get_audit_service()
                    asyncio.create_task(
                        audit_service.log_email_failed(
                            db=None,
                            user_id=user.id,
                            template_name="welcome",
                            error="Failed to send welcome email after retries",
                        )
                    )
                except Exception as audit_err:
                    logger.warning(f"Failed to log email failure to audit: {audit_err}")

            return success

        except Exception as e:
            logger.error(f"Error sending welcome email to {user.username}: {e}")
            # Log error to audit
            try:
                audit_service = get_audit_service()
                asyncio.create_task(
                    audit_service.log_email_failed(
                        db=None,
                        user_id=user.id,
                        template_name="welcome",
                        error=str(e),
                    )
                )
            except Exception as audit_err:
                logger.warning(f"Failed to log email error to audit: {audit_err}")
            return False

    async def _send_confirmation_email_internal(
        self, user: User, token: str
    ) -> bool:
        """Internal method to send confirmation email

        Args:
            user: User object
            token: Email confirmation token

        Returns:
            True if email sent successfully
        """
        try:
            # Prepare context for template
            context = {
                "username": user.username,
                "confirmation_link": (
                    f"https://codelab.local/confirm-email?token={token}"
                ),
                "expires_at": "24 hours from now",
                "to_email": user.email,
                "from_email": settings.smtp_from_email,
            }

            # Render template
            message = await self.template_engine.render_template(
                "confirmation", context
            )

            # Send with retry
            success = await self.retry_service.send_with_retry(
                message, max_retries=settings.smtp_max_retries
            )

            if success:
                logger.info(f"Confirmation email sent to {user.username}")
            else:
                logger.warning(
                    f"Failed to send confirmation email to {user.username}"
                )

            return success

        except Exception as e:
            logger.error(
                f"Error sending confirmation email to {user.username}: {e}"
            )
            return False

    async def _send_password_reset_email_internal(
        self, user: User, reset_token: str
    ) -> bool:
        """Internal method to send password reset email

        Args:
            user: User object
            reset_token: Password reset token

        Returns:
            True if email sent successfully
        """
        try:
            # Prepare context for template
            # Token expiration is 30 minutes (matches TOKEN_EXPIRATION_MINUTES in password_reset_service.py)
            context = {
                "username": user.username,
                "reset_link": (
                    f"https://codelab.local/reset-password?token={reset_token}"
                ),
                "expires_at": "30 minutes from now",
                "to_email": user.email,
                "from_email": settings.smtp_from_email,
            }

            # Render template
            message = await self.template_engine.render_template(
                "password_reset", context
            )

            # Send with retry
            success = await self.retry_service.send_with_retry(
                message, max_retries=settings.smtp_max_retries
            )

            if success:
                logger.info(f"Password reset email sent to {user.username}")
            else:
                logger.warning(
                    f"Failed to send password reset email to {user.username}"
                )

            return success

        except Exception as e:
            logger.error(
                f"Error sending password reset email to {user.username}: {e}"
            )
            return False

    async def _send_async(
        self, message, retry: bool = True
    ) -> bool:
        """Internal method for sending message (with optional retry)

        Args:
            message: EmailMessage to send
            retry: Whether to use retry logic

        Returns:
            True if sent successfully
        """
        if retry:
            return await self.retry_service.send_with_retry(
                message, max_retries=settings.smtp_max_retries
            )
        else:
            return await self.sender.send_email(message)
