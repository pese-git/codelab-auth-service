"""Unit tests for SMTP email sender"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest


class TestSMTPEmailSender:
    """Tests for SMTPEmailSender"""

    def test_mask_email_full_address(self):
        """Test email masking for full address"""
        from app.services.email_sender import SMTPEmailSender
        
        email = "john.doe@example.com"
        masked = SMTPEmailSender._mask_email(email)
        
        assert masked.startswith("j")
        assert "@example.com" in masked
        assert "john.doe" not in masked

    def test_mask_email_short_local_part(self):
        """Test email masking for short local part"""
        from app.services.email_sender import SMTPEmailSender
        
        email = "j@example.com"
        masked = SMTPEmailSender._mask_email(email)
        
        assert "example.com" in masked

    def test_mask_email_no_at_sign(self):
        """Test email masking for invalid email"""
        from app.services.email_sender import SMTPEmailSender
        
        email = "invalidemail"
        masked = SMTPEmailSender._mask_email(email)
        
        assert masked == "invalidemail"

    def test_mask_email_empty_string(self):
        """Test email masking for empty string"""
        from app.services.email_sender import SMTPEmailSender
        
        email = ""
        masked = SMTPEmailSender._mask_email(email)
        
        assert masked == ""

    def test_mask_email_preserves_domain(self):
        """Test that domain is preserved in masking"""
        from app.services.email_sender import SMTPEmailSender
        
        email = "user@mydomain.com"
        masked = SMTPEmailSender._mask_email(email)
        
        assert "mydomain.com" in masked

    @pytest.mark.asyncio
    async def test_create_mime_message(self):
        """Test MIME message creation"""
        from app.services.email_sender import SMTPEmailSender
        from tests.conftest import MockEmailMessage
        
        message = MockEmailMessage(
            subject="Test Subject",
            html_body="<p>Test</p>",
            text_body="Test",
            to="user@example.com",
            from_="sender@example.com",
            template_name="test",
        )
        
        mime_msg = SMTPEmailSender._create_mime_message(message)
        
        assert mime_msg["Subject"] == "Test Subject"
        assert mime_msg["From"] == "sender@example.com"
        assert mime_msg["To"] == "user@example.com"

    @pytest.mark.asyncio
    async def test_create_mime_message_multipart(self):
        """Test MIME message is multipart"""
        from app.services.email_sender import SMTPEmailSender
        from tests.conftest import MockEmailMessage
        
        message = MockEmailMessage(
            subject="Test",
            html_body="<p>HTML Content</p>",
            text_body="Text Content",
            to="test@example.com",
            from_="sender@example.com",
            template_name="test",
        )
        
        mime_msg = SMTPEmailSender._create_mime_message(message)
        
        # Should be multipart alternative
        assert mime_msg.get_content_type() == "multipart/alternative"
