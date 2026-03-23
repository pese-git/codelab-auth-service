"""SMTP email sender service for sending emails asynchronously"""

import asyncio
import logging
from typing import Optional

from aiosmtplib import SMTP, SMTPAuthenticationError, SMTPServerError

from app.core.config import settings
from app.services.email_templates import EmailMessage

logger = logging.getLogger("auth-service")


class SMTPEmailSender:
    """Asynchronous SMTP email sender with TLS support and error handling"""

    def __init__(self):
        """Initialize SMTP sender with configuration from settings

        Example:
            >>> sender = SMTPEmailSender()
            >>> success = await sender.send_email(message, timeout=30)
        """
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.smtp_use_tls = settings.smtp_use_tls
        self.smtp_timeout = settings.smtp_timeout

    async def send_email(
        self, message: EmailMessage, timeout: Optional[int] = None
    ) -> bool:
        """Send email asynchronously via SMTP

        Args:
            message: EmailMessage to send
            timeout: Timeout in seconds (uses default if not specified)

        Returns:
            True if email sent successfully, False otherwise

        Raises:
            SMTPServerError: For 4xx errors (retryable)
            asyncio.TimeoutError: On connection timeout (retryable)
            ConnectionError: On connection issues (retryable)

        Example:
            >>> message = EmailMessage(
            ...     subject="Test",
            ...     html_body="<p>Hello</p>",
            ...     text_body="Hello",
            ...     to="user@example.com",
            ...     from_="noreply@example.com",
            ...     template_name="test"
            ... )
            >>> success = await sender.send_email(message)
        """
        timeout = timeout or self.smtp_timeout

        try:
            async with SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                timeout=timeout,
            ) as smtp:
                # Use TLS if configured
                if self.smtp_use_tls:
                    await smtp.starttls()

                # Authenticate if credentials provided
                if self.smtp_username and self.smtp_password:
                    await smtp.login(self.smtp_username, self.smtp_password)

                # Send email
                await smtp.send_message(
                    self._create_mime_message(message)
                )

                logger.info(
                    f"Email sent successfully to {self._mask_email(message.to)} "
                    f"(template: {message.template_name})"
                )
                return True

        except SMTPAuthenticationError as e:
            # Authentication errors are permanent, don't retry
            logger.critical(
                f"SMTP authentication failed: {e}. "
                f"Check SMTP credentials in configuration."
            )
            return False

        except SMTPServerError as e:
            # Check error code
            if 500 <= e.code < 600:
                # 5xx errors are permanent, don't retry
                logger.error(
                    f"SMTP server error ({e.code}): {e}. "
                    f"To: {self._mask_email(message.to)}"
                )
                return False
            else:
                # 4xx errors are temporary, should retry
                logger.warning(
                    f"SMTP temporary error ({e.code}): {e}. "
                    f"To: {self._mask_email(message.to)}"
                )
                raise

        except asyncio.TimeoutError as e:
            logger.warning(
                f"SMTP connection timeout after {timeout}s. "
                f"To: {self._mask_email(message.to)}"
            )
            raise

        except ConnectionError as e:
            logger.warning(
                f"SMTP connection error: {e}. "
                f"To: {self._mask_email(message.to)}"
            )
            raise

        except Exception as e:
            logger.error(
                f"Unexpected error sending email to {self._mask_email(message.to)}: {e}"
            )
            raise

    @staticmethod
    def _create_mime_message(message: EmailMessage):
        """Create MIME message from EmailMessage

        Args:
            message: EmailMessage object

        Returns:
            email.message.EmailMessage suitable for SMTP

        Example:
            >>> from email.message import EmailMessage
            >>> mime_msg = SMTPEmailSender._create_mime_message(message)
        """
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        # Create multipart message
        mime_message = MIMEMultipart("alternative")
        mime_message["Subject"] = message.subject
        mime_message["From"] = message.from_
        mime_message["To"] = message.to

        # Attach text version first, then HTML (priority order)
        mime_message.attach(MIMEText(message.text_body, "plain"))
        mime_message.attach(MIMEText(message.html_body, "html"))

        return mime_message

    @staticmethod
    def _mask_email(email: str) -> str:
        """Mask email address for logging (show only first letter + domain)

        Args:
            email: Email address to mask

        Returns:
            Masked email address

        Example:
            >>> SMTPEmailSender._mask_email("user@example.com")
            'u***@example.com'
        """
        if "@" not in email:
            return email

        local, domain = email.split("@", 1)
        if len(local) <= 1:
            masked_local = "*" * len(local)
        else:
            masked_local = local[0] + "*" * (len(local) - 1)

        return f"{masked_local}@{domain}"
