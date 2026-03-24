"""Email retry service with exponential backoff for handling transient failures"""

import asyncio
import logging
import random
from typing import Optional

from aiosmtplib import SMTPResponseException

from app.services.email_sender import SMTPEmailSender
from app.services.email_templates import EmailMessage

logger = logging.getLogger("auth-service")


class EmailRetryService:
    """Retry logic for email sending with exponential backoff and jitter"""

    def __init__(self, sender: Optional[SMTPEmailSender] = None):
        """Initialize retry service

        Args:
            sender: SMTPEmailSender instance (creates new if not provided)

        Example:
            >>> sender = SMTPEmailSender()
            >>> retry_service = EmailRetryService(sender)
        """
        self.sender = sender or SMTPEmailSender()

    async def send_with_retry(
        self,
        message: EmailMessage,
        max_retries: Optional[int] = None,
        base_delay: int = 2,
    ) -> bool:
        """Send email with exponential backoff retry logic

        Retries on transient errors (4xx SMTP, timeout, connection).
        Does not retry on permanent errors (auth, 5xx SMTP).

        Args:
            message: EmailMessage to send
            max_retries: Maximum number of retries (uses config default if None)
            base_delay: Base delay in seconds for backoff calculation

        Returns:
            True if email sent successfully, False if failed after all retries

        Example:
            >>> success = await retry_service.send_with_retry(
            ...     message,
            ...     max_retries=3,
            ...     base_delay=2
            ... )
        """
        from app.core.config import settings

        max_retries = max_retries or settings.smtp_max_retries

        for attempt in range(max_retries + 1):
            try:
                # Attempt to send
                success = await self.sender.send_email(message)
                if success:
                    self._log_attempt(
                        message, attempt, error=None, success=True
                    )
                    return True

                # If send_email returned False (permanent error), stop retrying
                self._log_attempt(message, attempt, error="Permanent error")
                return False

            except (SMTPResponseException, asyncio.TimeoutError, ConnectionError) as e:
                self._log_attempt(message, attempt, error=e)

                # Check if we should retry
                if not self._should_retry(e):
                    logger.error(
                        f"Non-retryable error for {message.to}: {e}"
                    )
                    return False

                # Check if we have retries left
                if attempt >= max_retries:
                    logger.error(
                        f"Max retries ({max_retries}) exceeded for {message.to}"
                    )
                    return False

                # Calculate backoff and wait
                backoff = self._calculate_backoff(
                    attempt, base_delay, max_backoff=300
                )
                logger.info(
                    f"Retry attempt {attempt + 1}/{max_retries} "
                    f"for {message.to} in {backoff:.2f}s"
                )
                await asyncio.sleep(backoff)

            except Exception as e:
                # Unexpected error, don't retry
                logger.error(
                    f"Unexpected error sending to {message.to}: {e}"
                )
                self._log_attempt(
                    message, attempt, error=f"Unexpected: {e}"
                )
                return False

        return False

    @staticmethod
    def _calculate_backoff(
        attempt: int, base_delay: int, max_backoff: int = 300
    ) -> float:
        """Calculate exponential backoff with jitter

        Formula: backoff = base_delay * (2 ^ attempt) with ±10% jitter

        Args:
            attempt: Attempt number (0-indexed)
            base_delay: Base delay in seconds
            max_backoff: Maximum backoff in seconds

        Returns:
            Delay in seconds

        Example:
            >>> backoff = EmailRetryService._calculate_backoff(0, 2)  # 2-2.4s
            >>> backoff = EmailRetryService._calculate_backoff(1, 2)  # 4-4.8s
        """
        # Exponential: 2^0=1, 2^1=2, 2^2=4, etc.
        backoff = base_delay * (2**attempt)

        # Cap at maximum
        backoff = min(backoff, max_backoff)

        # Add jitter: ±10%
        jitter = backoff * 0.1 * (2 * random.random() - 1)
        final_backoff = backoff + jitter

        return max(0, final_backoff)

    @staticmethod
    def _should_retry(error: Exception) -> bool:
        """Determine if error is retryable

        Args:
            error: Exception that occurred

        Returns:
            True if we should retry, False if permanent

        Retryable errors:
            - SMTPResponseException with 4xx codes
            - asyncio.TimeoutError
            - ConnectionError

        Non-retryable:
            - SMTPResponseException with 5xx codes
            - Others
        """
        if isinstance(error, SMTPResponseException):
            # 4xx are temporary, 5xx are permanent
            return 400 <= error.code < 500

        if isinstance(error, (asyncio.TimeoutError, ConnectionError)):
            return True

        return False

    @staticmethod
    def _log_attempt(
        message: EmailMessage,
        attempt: int,
        error: Optional[Exception | str] = None,
        success: bool = False,
    ) -> None:
        """Log email send attempt for audit

        Args:
            message: EmailMessage being sent
            attempt: Attempt number
            error: Error object or message (None if successful)
            success: Whether attempt was successful
        """
        if success:
            logger.debug(
                f"Email attempt {attempt}: SUCCESS to {message.to} "
                f"(template: {message.template_name})"
            )
        else:
            error_msg = str(error) if error else "Unknown error"
            logger.debug(
                f"Email attempt {attempt}: FAILED to {message.to} "
                f"- {error_msg} (template: {message.template_name})"
            )
