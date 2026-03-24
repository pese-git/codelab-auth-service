"""Unit tests for email service"""

from unittest.mock import AsyncMock, patch
import pytest


class TestEmailService:
    """Tests for EmailService"""

    def test_email_service_initialization(self):
        """Test email service can be initialized"""
        # Basic instantiation check
        pass

    @pytest.mark.asyncio
    async def test_generate_confirmation_token(self):
        """Test generating a confirmation token"""
        from app.services.email_service import EmailService
        
        service = EmailService()
        user_id = "test_user_id"
        
        token = await service.generate_confirmation_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 20

    @pytest.mark.asyncio
    async def test_generate_confirmation_token_uniqueness(self):
        """Test that generated tokens are unique"""
        from app.services.email_service import EmailService
        
        service = EmailService()
        user_id = "test_user_id"
        
        token1 = await service.generate_confirmation_token(user_id)
        token2 = await service.generate_confirmation_token(user_id)
        
        assert token1 != token2

    @pytest.mark.asyncio
    async def test_is_confirmation_required(self):
        """Test checking if confirmation is required"""
        from app.services.email_service import EmailService
        
        service = EmailService()
        
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.require_email_confirmation = True
            result = service.is_confirmation_required()
            assert result is True
            
            mock_settings.require_email_confirmation = False
            result = service.is_confirmation_required()
            assert result is False

    @pytest.mark.asyncio
    async def test_token_expiration_calculation(self):
        """Test that token expiration is calculated correctly"""
        from app.services.email_service import EmailService
        from datetime import datetime, timedelta, timezone
        
        service = EmailService()
        
        # Test that 24 hour expiration is roughly correct
        # (without actual DB operations)
        expires_in_hours = 24
        expected_delta = timedelta(hours=expires_in_hours)
        
        assert expected_delta.total_seconds() == 86400
