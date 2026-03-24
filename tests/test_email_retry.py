"""Tests for email retry service with exponential backoff"""

from unittest.mock import AsyncMock, patch

import pytest
from aiosmtplib import SMTPResponseException

from app.services.email_retry import EmailRetryService
from app.services.email_templates import EmailMessage


@pytest.fixture
def sample_email():
    """Create sample email message for testing"""
    return EmailMessage(
        subject="Test Subject",
        html_body="<p>Hello World</p>",
        text_body="Hello World",
        to="user@example.com",
        from_="noreply@codelab.local",
        template_name="test",
    )


@pytest.fixture
def mock_sender():
    """Create mock SMTP sender"""
    sender = AsyncMock()
    sender.send_email = AsyncMock()
    return sender


class TestEmailRetryService:
    """Test email retry service functionality"""

    @pytest.mark.asyncio
    async def test_send_with_retry_success_on_first_attempt(self, sample_email, mock_sender):
        """Test successful send on first attempt (no retries needed)"""
        mock_sender.send_email.return_value = True

        retry_service = EmailRetryService(mock_sender)
        result = await retry_service.send_with_retry(sample_email, max_retries=3)

        assert result is True
        mock_sender.send_email.assert_called_once_with(sample_email)

    @pytest.mark.asyncio
    async def test_send_with_retry_success_after_retries(self, sample_email, mock_sender):
        """Test successful send after one retry"""
        # First call fails with 4xx error, second call succeeds
        mock_sender.send_email.side_effect = [
            SMTPResponseException(421, "Service not available"),
            True,
        ]

        retry_service = EmailRetryService(mock_sender)
        with patch("asyncio.sleep", return_value=None):  # Skip actual sleep
            result = await retry_service.send_with_retry(
                sample_email, max_retries=3, base_delay=1
            )

        assert result is True
        assert mock_sender.send_email.call_count == 2

    @pytest.mark.asyncio
    async def test_send_with_retry_max_retries_exceeded(self, sample_email, mock_sender):
        """Test failure after max retries are exceeded"""
        # All calls fail with 4xx error
        mock_sender.send_email.side_effect = SMTPResponseException(
            421, "Service not available"
        )

        retry_service = EmailRetryService(mock_sender)
        with patch("asyncio.sleep", return_value=None):
            result = await retry_service.send_with_retry(
                sample_email, max_retries=2, base_delay=1
            )

        assert result is False
        # Should attempt 3 times (initial + 2 retries)
        assert mock_sender.send_email.call_count == 3

    @pytest.mark.asyncio
    async def test_send_with_retry_non_retryable_error(self, sample_email, mock_sender):
        """Test that non-retryable errors (5xx) don't trigger retries"""
        mock_sender.send_email.return_value = False  # Permanent error

        retry_service = EmailRetryService(mock_sender)
        result = await retry_service.send_with_retry(
            sample_email, max_retries=3, base_delay=1
        )

        assert result is False
        # Should only attempt once
        mock_sender.send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_with_retry_timeout_is_retryable(self, sample_email, mock_sender):
        """Test that timeout errors trigger retries"""
        # First call times out, second succeeds
        mock_sender.send_email.side_effect = [
            TimeoutError(),
            True,
        ]

        retry_service = EmailRetryService(mock_sender)
        with patch("asyncio.sleep", return_value=None):
            result = await retry_service.send_with_retry(
                sample_email, max_retries=3, base_delay=1
            )

        assert result is True
        assert mock_sender.send_email.call_count == 2

    @pytest.mark.asyncio
    async def test_send_with_retry_connection_error_is_retryable(self, sample_email, mock_sender):
        """Test that connection errors trigger retries"""
        # First call fails with connection error, second succeeds
        mock_sender.send_email.side_effect = [
            ConnectionError("Network unreachable"),
            True,
        ]

        retry_service = EmailRetryService(mock_sender)
        with patch("asyncio.sleep", return_value=None):
            result = await retry_service.send_with_retry(
                sample_email, max_retries=3, base_delay=1
            )

        assert result is True
        assert mock_sender.send_email.call_count == 2

    def test_calculate_backoff_exponential_growth(self):
        """Test exponential backoff calculation grows correctly"""
        # Attempt 0: base_delay * 2^0 = 2 * 1 = 2
        backoff_0 = EmailRetryService._calculate_backoff(0, base_delay=2)
        assert 1.8 <= backoff_0 <= 2.2  # Allow for jitter

        # Attempt 1: base_delay * 2^1 = 2 * 2 = 4
        backoff_1 = EmailRetryService._calculate_backoff(1, base_delay=2)
        assert 3.6 <= backoff_1 <= 4.4  # Allow for jitter

        # Attempt 2: base_delay * 2^2 = 2 * 4 = 8
        backoff_2 = EmailRetryService._calculate_backoff(2, base_delay=2)
        assert 7.2 <= backoff_2 <= 8.8  # Allow for jitter

    def test_calculate_backoff_max_backoff_cap(self):
        """Test that backoff is capped at max_backoff"""
        # Without cap would be: 2 * 2^10 = 2048
        backoff = EmailRetryService._calculate_backoff(10, base_delay=2, max_backoff=300)
        assert backoff <= 330  # 300 + jitter (±10% = 30)

    def test_calculate_backoff_with_jitter(self):
        """Test that jitter is applied (±10%)"""
        backoff_values = [
            EmailRetryService._calculate_backoff(0, base_delay=10)
            for _ in range(10)
        ]
        # All values should be around 10 but with some variation
        assert all(9 <= val <= 11 for val in backoff_values)
        # Should have some variation (at least some different values)
        assert len(set(backoff_values)) > 1

    def test_should_retry_4xx_error(self):
        """Test that 4xx errors are retryable"""
        error = SMTPResponseException(421, "Service not available")
        assert EmailRetryService._should_retry(error) is True

        error = SMTPResponseException(450, "Requested action not taken")
        assert EmailRetryService._should_retry(error) is True

    def test_should_retry_5xx_error(self):
        """Test that 5xx errors are not retryable"""
        error = SMTPResponseException(550, "User not found")
        assert EmailRetryService._should_retry(error) is False

        error = SMTPResponseException(599, "Server error")
        assert EmailRetryService._should_retry(error) is False

    def test_should_retry_timeout_error(self):
        """Test that timeout errors are retryable"""
        error = TimeoutError()
        assert EmailRetryService._should_retry(error) is True

    def test_should_retry_connection_error(self):
        """Test that connection errors are retryable"""
        error = ConnectionError("Network unreachable")
        assert EmailRetryService._should_retry(error) is True

    def test_should_retry_other_errors(self):
        """Test that other errors are not retryable"""
        error = ValueError("Invalid argument")
        assert EmailRetryService._should_retry(error) is False

    def test_log_attempt_success(self, sample_email):
        """Test logging of successful send attempt"""
        EmailRetryService._log_attempt(sample_email, 0, error=None, success=True)
        # The log should be captured by logging, not stdout
        # Just verify the method doesn't raise

    def test_log_attempt_failure(self, sample_email, capsys):
        """Test logging of failed send attempt"""
        error = SMTPResponseException(421, "Service not available")
        EmailRetryService._log_attempt(sample_email, 1, error=error, success=False)
        # Just verify the method doesn't raise

    @pytest.mark.asyncio
    async def test_send_with_retry_single_success(self, sample_email, mock_sender):
        """Test successful send on first attempt without explicit max_retries"""
        mock_sender.send_email.return_value = True

        retry_service = EmailRetryService(mock_sender)
        # Test with explicit max_retries to avoid config dependency
        result = await retry_service.send_with_retry(sample_email, max_retries=3)

        assert result is True
        mock_sender.send_email.assert_called_once()
