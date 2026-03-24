"""Unit tests for email retry service with exponential backoff"""

import asyncio
from unittest.mock import AsyncMock

import pytest
from aiosmtplib import SMTPResponseException


class TestEmailRetryService:
    """Tests for EmailRetryService"""

    def test_calculate_backoff_first_attempt(self):
        """Test backoff calculation for first retry"""
        from app.services.email_retry import EmailRetryService
        
        backoff = EmailRetryService._calculate_backoff(0, base_delay=2)
        
        # Should be between 2 * (2^0) = 2 and 2.2 (with jitter)
        assert 1.8 <= backoff <= 2.2

    def test_calculate_backoff_second_attempt(self):
        """Test backoff calculation for second retry"""
        from app.services.email_retry import EmailRetryService
        
        backoff = EmailRetryService._calculate_backoff(1, base_delay=2)
        
        # Should be between 2 * (2^1) = 4 and 4.4 (with jitter)
        assert 3.6 <= backoff <= 4.4

    def test_calculate_backoff_exponential_growth(self):
        """Test exponential growth of backoff"""
        from app.services.email_retry import EmailRetryService
        
        backoff_0 = EmailRetryService._calculate_backoff(0, base_delay=2, max_backoff=1000)
        backoff_1 = EmailRetryService._calculate_backoff(1, base_delay=2, max_backoff=1000)
        backoff_2 = EmailRetryService._calculate_backoff(2, base_delay=2, max_backoff=1000)
        
        # Should roughly double each time (with jitter)
        assert backoff_0 < backoff_1 < backoff_2

    def test_calculate_backoff_max_cap(self):
        """Test backoff is capped at maximum"""
        from app.services.email_retry import EmailRetryService
        
        backoff = EmailRetryService._calculate_backoff(10, base_delay=2, max_backoff=300)
        
        assert backoff <= 330  # max_backoff + 10% jitter

    def test_should_retry_smtp_4xx_error(self):
        """Test that 4xx SMTP errors are retryable"""
        from app.services.email_retry import EmailRetryService
        
        error = SMTPResponseException(450, "Temporary failure")
        
        should_retry = EmailRetryService._should_retry(error)
        
        assert should_retry is True

    def test_should_retry_smtp_5xx_error(self):
        """Test that 5xx SMTP errors are NOT retryable"""
        from app.services.email_retry import EmailRetryService
        
        error = SMTPResponseException(550, "User not found")
        
        should_retry = EmailRetryService._should_retry(error)
        
        assert should_retry is False

    def test_should_retry_timeout_error(self):
        """Test that timeout errors are retryable"""
        from app.services.email_retry import EmailRetryService
        
        error = asyncio.TimeoutError("Connection timeout")
        
        should_retry = EmailRetryService._should_retry(error)
        
        assert should_retry is True

    def test_should_retry_connection_error(self):
        """Test that connection errors are retryable"""
        from app.services.email_retry import EmailRetryService
        
        error = ConnectionError("Connection refused")
        
        should_retry = EmailRetryService._should_retry(error)
        
        assert should_retry is True

    def test_should_retry_other_error(self):
        """Test that other errors are NOT retryable"""
        from app.services.email_retry import EmailRetryService
        
        error = ValueError("Some other error")
        
        should_retry = EmailRetryService._should_retry(error)
        
        assert should_retry is False

    def test_should_retry_smtp_400_boundary(self):
        """Test boundary for 4xx errors"""
        from app.services.email_retry import EmailRetryService
        
        # Test 400 (first 4xx)
        error_400 = SMTPResponseException(400, "Temp")
        assert EmailRetryService._should_retry(error_400) is True
        
        # Test 499 (last 4xx)
        error_499 = SMTPResponseException(499, "Temp")
        assert EmailRetryService._should_retry(error_499) is True
        
        # Test 500 (first 5xx)
        error_500 = SMTPResponseException(500, "Perm")
        assert EmailRetryService._should_retry(error_500) is False

    def test_log_attempt_success(self):
        """Test logging of successful attempt"""
        from app.services.email_retry import EmailRetryService
        from tests.conftest import MockEmailMessage
        
        message = MockEmailMessage(
            subject="Test",
            html_body="<p>Test</p>",
            text_body="Test",
            to="test@example.com",
            from_="sender@example.com",
            template_name="test",
        )
        
        # Should not raise
        EmailRetryService._log_attempt(message, attempt=0, error=None, success=True)

    def test_log_attempt_failure(self):
        """Test logging of failed attempt"""
        from app.services.email_retry import EmailRetryService
        from tests.conftest import MockEmailMessage
        
        message = MockEmailMessage(
            subject="Test",
            html_body="<p>Test</p>",
            text_body="Test",
            to="test@example.com",
            from_="sender@example.com",
            template_name="test",
        )
        
        error = Exception("Test error")
        # Should not raise
        EmailRetryService._log_attempt(message, attempt=1, error=error, success=False)
