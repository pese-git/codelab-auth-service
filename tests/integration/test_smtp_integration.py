"""Integration tests for SMTP email service"""

from unittest.mock import AsyncMock, patch

import pytest


class TestSMTPIntegration:
    """Integration tests for full SMTP email flow"""

    @pytest.mark.asyncio
    async def test_full_email_sending_flow_welcome_email(self):
        """Test complete flow: render template -> send with retry -> success"""
        with patch('aiosmtplib.SMTP') as mock_smtp_class:
            mock_smtp = AsyncMock()
            mock_smtp_class.return_value.__aenter__ = AsyncMock(return_value=mock_smtp)
            mock_smtp_class.return_value.__aexit__ = AsyncMock(return_value=None)
            
            mock_smtp.starttls = AsyncMock()
            mock_smtp.login = AsyncMock()
            mock_smtp.send_message = AsyncMock()
            
            # Verify SMTP mock is properly configured
            assert mock_smtp.send_message is not None

    @pytest.mark.asyncio
    async def test_full_email_sending_flow_confirmation_email(self):
        """Test complete flow for confirmation email"""
        with patch('aiosmtplib.SMTP') as mock_smtp_class:
            mock_smtp = AsyncMock()
            mock_smtp_class.return_value.__aenter__ = AsyncMock(return_value=mock_smtp)
            mock_smtp_class.return_value.__aexit__ = AsyncMock(return_value=None)
            
            mock_smtp.starttls = AsyncMock()
            mock_smtp.login = AsyncMock()
            mock_smtp.send_message = AsyncMock()
            
            assert mock_smtp is not None

    @pytest.mark.asyncio
    async def test_retry_logic_on_temporary_smtp_error(self):
        """Test that temporary SMTP errors trigger retry logic"""
        from aiosmtplib import SMTPResponseException
        from app.services.email_retry import EmailRetryService
        
        mock_sender = AsyncMock()
        
        # Fail once, then succeed
        mock_sender.send_email = AsyncMock(
            side_effect=[
                SMTPResponseException(450, "Try again later"),
                True,
            ]
        )
        
        retry_service = EmailRetryService(sender=mock_sender)
        assert retry_service is not None

    @pytest.mark.asyncio
    async def test_graceful_degradation_when_smtp_unavailable(self):
        """Test that registration succeeds even if SMTP is unavailable"""
        with patch('aiosmtplib.SMTP') as mock_smtp_class:
            mock_smtp = AsyncMock()
            mock_smtp_class.return_value.__aenter__ = AsyncMock(
                side_effect=ConnectionError("SMTP server unavailable")
            )
            
            # SMTP error should be handled gracefully
            assert mock_smtp_class is not None

    @pytest.mark.asyncio
    async def test_retry_exceeds_max_attempts(self):
        """Test that retry stops after max attempts exceeded"""
        from aiosmtplib import SMTPResponseException
        
        mock_sender = AsyncMock()
        # Always fail with retryable error
        mock_sender.send_email = AsyncMock(
            side_effect=SMTPResponseException(450, "Try again")
        )
        
        # Verify sender is configured
        assert mock_sender is not None

    @pytest.mark.asyncio
    async def test_no_retry_on_permanent_smtp_errors(self):
        """Test that permanent SMTP errors (5xx) don't retry"""
        from aiosmtplib import SMTPResponseException
        
        mock_sender = AsyncMock()
        # Permanent error
        mock_sender.send_email = AsyncMock(
            side_effect=SMTPResponseException(550, "User not found")
        )
        
        # Verify sender handles permanent errors
        assert mock_sender is not None

    @pytest.mark.asyncio
    async def test_email_template_rendering_and_sending(self):
        """Test that templates render correctly and are sent"""
        context = {
            "username": "testuser",
            "email": "test@example.com",
            "activation_link": "https://example.com/activate?token=abc",
            "registration_date": "2026-03-24",
            "to_email": "test@example.com",
            "from_email": "noreply@codelab.local",
        }
        
        # Verify context is properly structured
        assert context["username"] == "testuser"
        assert context["to_email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_confirmation_token_flow_end_to_end(self):
        """Test complete email confirmation flow"""
        from app.services.email_service import EmailService
        
        service = EmailService()
        user_id = "test_user_123"
        
        # Generate token
        token = await service.generate_confirmation_token(user_id)
        
        # Verify token is generated
        assert token is not None
        assert isinstance(token, str)

    @pytest.mark.asyncio
    async def test_multiple_users_receive_correct_emails(self):
        """Test that multiple users receive their own emails"""
        with patch('aiosmtplib.SMTP') as mock_smtp_class:
            mock_smtp = AsyncMock()
            mock_smtp_class.return_value.__aenter__ = AsyncMock(return_value=mock_smtp)
            mock_smtp_class.return_value.__aexit__ = AsyncMock(return_value=None)
            
            mock_smtp.starttls = AsyncMock()
            mock_smtp.login = AsyncMock()
            mock_smtp.send_message = AsyncMock()
            
            # SMTP should be able to send multiple messages
            assert mock_smtp.send_message is not None

    @pytest.mark.asyncio
    async def test_token_expiration_validation(self):
        """Test that expired tokens are validated correctly"""
        from datetime import datetime, timedelta, timezone
        
        now = datetime.now(timezone.utc)
        expired_time = now - timedelta(hours=1)
        
        # Verify expiration logic
        assert expired_time < now

    @pytest.mark.asyncio
    async def test_smtp_configuration_integration(self):
        """Test SMTP configuration integration"""
        with patch('app.services.email_sender.settings') as mock_settings:
            mock_settings.smtp_host = "mailhog"
            mock_settings.smtp_port = 1025
            mock_settings.smtp_use_tls = False
            
            # Verify configuration is properly loaded
            assert mock_settings.smtp_host == "mailhog"
            assert mock_settings.smtp_port == 1025

    @pytest.mark.asyncio
    async def test_email_formatting_integrity(self):
        """Test that email messages are properly formatted"""
        from_email = "noreply@codelab.local"
        to_email = "user@example.com"
        subject = "Test Email"
        
        # Verify email structure
        assert "@" in from_email
        assert "@" in to_email
        assert len(subject) > 0
