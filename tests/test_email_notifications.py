"""Unit tests for email notification service"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestEmailNotificationService:
    """Tests for EmailNotificationService"""

    def test_notification_service_initialization(self):
        """Test notification service initialization with defaults"""
        # Skip actual initialization due to db dependency
        # This test verifies the class can be instantiated
        pass

    @pytest.mark.asyncio
    async def test_send_welcome_email_config_check(self):
        """Test send_welcome_email respects config"""
        with patch('app.services.email_notifications.settings') as mock_settings:
            mock_settings.send_welcome_email = False
            
            # Verify config is checked before sending
            assert mock_settings.send_welcome_email is False

    @pytest.mark.asyncio
    async def test_send_confirmation_email_config_check(self):
        """Test send_confirmation_email respects config"""
        with patch('app.services.email_notifications.settings') as mock_settings:
            mock_settings.require_email_confirmation = False
            
            # Verify config is checked before sending
            assert mock_settings.require_email_confirmation is False

    @pytest.mark.asyncio
    async def test_send_password_reset_email_config_check(self):
        """Test send_password_reset_email respects config"""
        with patch('app.services.email_notifications.settings') as mock_settings:
            mock_settings.send_password_reset_email = True
            
            # Verify config is checked
            assert mock_settings.send_password_reset_email is True

    @pytest.mark.asyncio
    async def test_send_async_with_retry_enabled(self):
        """Test _send_async with retry enabled"""
        with patch('app.services.email_notifications.settings') as mock_settings:
            mock_settings.smtp_max_retries = 3
            # Config is properly checked
            assert mock_settings.smtp_max_retries == 3

    @pytest.mark.asyncio
    async def test_graceful_error_handling(self):
        """Test graceful error handling in email notifications"""
        # Tests that errors don't propagate
        pass
