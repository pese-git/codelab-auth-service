"""Tests for SMTP email sender functionality"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from aiosmtplib import SMTPAuthenticationError, SMTPResponseException

from app.services.email_sender import SMTPEmailSender
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


class TestSMTPEmailSender:
    """Test SMTP email sender functionality"""

    @pytest.mark.asyncio
    @patch("app.services.email_sender.settings")
    async def test_send_email_success(self, mock_settings, sample_email):
        """Test successful email sending via SMTP"""
        # Configure mock settings
        mock_settings.smtp_host = "localhost"
        mock_settings.smtp_port = 587
        mock_settings.smtp_username = "user"
        mock_settings.smtp_password = "pass"
        mock_settings.smtp_use_tls = True
        mock_settings.smtp_timeout = 30

        sender = SMTPEmailSender()

        # Mock the SMTP connection
        with patch("app.services.email_sender.SMTP") as mock_smtp_class:
            mock_smtp = AsyncMock()
            mock_smtp_class.return_value.__aenter__.return_value = mock_smtp

            result = await sender.send_email(sample_email)

            assert result is True
            mock_smtp.starttls.assert_called_once()
            mock_smtp.login.assert_called_once_with("user", "pass")
            mock_smtp.send_message.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.email_sender.settings")
    async def test_send_email_authentication_error(self, mock_settings, sample_email):
        """Test handling of SMTP authentication errors"""
        mock_settings.smtp_host = "localhost"
        mock_settings.smtp_port = 587
        mock_settings.smtp_username = "wrong_user"
        mock_settings.smtp_password = "wrong_pass"
        mock_settings.smtp_use_tls = True
        mock_settings.smtp_timeout = 30

        sender = SMTPEmailSender()

        # Mock SMTP authentication error
        with patch("app.services.email_sender.SMTP") as mock_smtp_class:
            mock_smtp = AsyncMock()
            mock_smtp.login.side_effect = SMTPAuthenticationError(
                535, "5.7.8 Username and Password not accepted"
            )
            mock_smtp_class.return_value.__aenter__.return_value = mock_smtp

            result = await sender.send_email(sample_email)

            assert result is False
            mock_smtp.login.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.email_sender.settings")
    async def test_send_email_server_error_5xx(self, mock_settings, sample_email):
        """Test handling of SMTP 5xx server errors (permanent)"""
        mock_settings.smtp_host = "localhost"
        mock_settings.smtp_port = 587
        mock_settings.smtp_username = "user"
        mock_settings.smtp_password = "pass"
        mock_settings.smtp_use_tls = True
        mock_settings.smtp_timeout = 30

        sender = SMTPEmailSender()

        # Mock SMTP 5xx error
        with patch("app.services.email_sender.SMTP") as mock_smtp_class:
            mock_smtp = AsyncMock()
            mock_smtp.send_message.side_effect = SMTPResponseException(
                550, "5.5.0 Requested action not taken"
            )
            mock_smtp_class.return_value.__aenter__.return_value = mock_smtp

            result = await sender.send_email(sample_email)

            assert result is False

    @pytest.mark.asyncio
    @patch("app.services.email_sender.settings")
    async def test_send_email_server_error_4xx(self, mock_settings, sample_email):
        """Test handling of SMTP 4xx server errors (temporary, should raise)"""
        mock_settings.smtp_host = "localhost"
        mock_settings.smtp_port = 587
        mock_settings.smtp_username = "user"
        mock_settings.smtp_password = "pass"
        mock_settings.smtp_use_tls = True
        mock_settings.smtp_timeout = 30

        sender = SMTPEmailSender()

        # Mock SMTP 4xx error
        with patch("app.services.email_sender.SMTP") as mock_smtp_class:
            mock_smtp = AsyncMock()
            mock_smtp.send_message.side_effect = SMTPResponseException(
                421, "4.2.1 Service not available"
            )
            mock_smtp_class.return_value.__aenter__.return_value = mock_smtp

            with pytest.raises(SMTPResponseException):
                await sender.send_email(sample_email)

    @pytest.mark.asyncio
    @patch("app.services.email_sender.settings")
    async def test_send_email_timeout(self, mock_settings, sample_email):
        """Test handling of connection timeout"""
        mock_settings.smtp_host = "localhost"
        mock_settings.smtp_port = 587
        mock_settings.smtp_username = "user"
        mock_settings.smtp_password = "pass"
        mock_settings.smtp_use_tls = True
        mock_settings.smtp_timeout = 5

        sender = SMTPEmailSender()

        # Mock timeout error
        with patch("app.services.email_sender.SMTP") as mock_smtp_class:
            mock_smtp_class.return_value.__aenter__.side_effect = TimeoutError()

            with pytest.raises(asyncio.TimeoutError):
                await sender.send_email(sample_email)

    @pytest.mark.asyncio
    @patch("app.services.email_sender.settings")
    async def test_send_email_connection_error(self, mock_settings, sample_email):
        """Test handling of connection errors"""
        mock_settings.smtp_host = "nonexistent.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_username = "user"
        mock_settings.smtp_password = "pass"
        mock_settings.smtp_use_tls = True
        mock_settings.smtp_timeout = 30

        sender = SMTPEmailSender()

        # Mock connection error
        with patch("app.services.email_sender.SMTP") as mock_smtp_class:
            mock_smtp_class.return_value.__aenter__.side_effect = ConnectionError(
                "Network unreachable"
            )

            with pytest.raises(ConnectionError):
                await sender.send_email(sample_email)

    def test_create_mime_message(self, sample_email):
        """Test MIME message creation from EmailMessage"""
        mime_msg = SMTPEmailSender._create_mime_message(sample_email)

        assert mime_msg["Subject"] == "Test Subject"
        assert mime_msg["From"] == "noreply@codelab.local"
        assert mime_msg["To"] == "user@example.com"
        # Check that it's a multipart message with both text and HTML
        assert mime_msg.is_multipart()

    def test_mask_email_full_local(self):
        """Test email masking with full local part"""
        email = "testuser@example.com"
        masked = SMTPEmailSender._mask_email(email)
        # testuser = 8 chars, so t + 7 asterisks = t*******@example.com
        assert masked == "t*******@example.com"

    def test_mask_email_single_character_local(self):
        """Test email masking with single character local part"""
        email = "a@example.com"
        masked = SMTPEmailSender._mask_email(email)
        assert masked == "*@example.com"

    def test_mask_email_without_at_symbol(self):
        """Test email masking with invalid email format"""
        email = "notanemail"
        masked = SMTPEmailSender._mask_email(email)
        assert masked == "notanemail"

    @pytest.mark.asyncio
    @patch("app.services.email_sender.settings")
    async def test_send_email_without_tls(self, mock_settings, sample_email):
        """Test email sending without TLS"""
        mock_settings.smtp_host = "localhost"
        mock_settings.smtp_port = 25
        mock_settings.smtp_username = None
        mock_settings.smtp_password = None
        mock_settings.smtp_use_tls = False
        mock_settings.smtp_timeout = 30

        sender = SMTPEmailSender()

        # Mock the SMTP connection
        with patch("app.services.email_sender.SMTP") as mock_smtp_class:
            mock_smtp = AsyncMock()
            mock_smtp_class.return_value.__aenter__.return_value = mock_smtp

            result = await sender.send_email(sample_email)

            assert result is True
            # starttls should not be called when TLS is disabled
            mock_smtp.starttls.assert_not_called()
            # login should not be called when credentials are not provided
            mock_smtp.login.assert_not_called()
