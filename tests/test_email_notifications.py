"""Tests for email notification service"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.email_notifications import EmailNotificationService
from tests.conftest import MockEmailMessage, MockUser


@pytest.fixture
def mock_user():
    """Create mock user for testing"""
    return MockUser(
        id="550e8400-e29b-41d4-a716-446655440000",
        username="testuser",
        email="testuser@example.com",
        password_hash="hashed_password",
        email_confirmed=False,
    )


@pytest.fixture
def mock_template_engine():
    """Create mock template engine"""
    engine = AsyncMock()
    engine.render_template = AsyncMock(
        return_value=MockEmailMessage(
            subject="Test Subject",
            html_body="<p>Test</p>",
            text_body="Test",
            to="test@example.com",
            from_="noreply@codelab.local",
            template_name="test",
        )
    )
    return engine


@pytest.fixture
def mock_smtp_sender():
    """Create mock SMTP sender"""
    sender = AsyncMock()
    sender.send_email = AsyncMock(return_value=True)
    return sender


@pytest.fixture
def mock_retry_service():
    """Create mock retry service"""
    service = AsyncMock()
    service.send_with_retry = AsyncMock(return_value=True)
    return service


class TestEmailNotificationService:
    """Test email notification service"""

    @pytest.mark.asyncio
    async def test_send_welcome_email_success(
        self, mock_user, mock_template_engine, mock_smtp_sender, mock_retry_service
    ):
        """Test sending welcome email to new user"""
        service = EmailNotificationService(
            template_engine=mock_template_engine,
            sender=mock_smtp_sender,
            retry_service=mock_retry_service,
        )

        # Send synchronously to avoid background task issues
        result = await service.send_welcome_email(mock_user, background=False)

        assert result is True
        mock_template_engine.render_template.assert_called_once()
        # Check that template was called with "welcome"
        assert "welcome" in str(mock_template_engine.render_template.call_args).lower()

    @pytest.mark.asyncio
    async def test_send_confirmation_email_success(
        self, mock_user, mock_template_engine, mock_smtp_sender, mock_retry_service
    ):
        """Test sending confirmation email with token"""
        service = EmailNotificationService(
            template_engine=mock_template_engine,
            sender=mock_smtp_sender,
            retry_service=mock_retry_service,
        )

        result = await service.send_confirmation_email(
            mock_user, token="test_token_123", background=False
        )

        assert result is True
        mock_template_engine.render_template.assert_called_once()
        # Check that template was called with "confirmation"
        assert "confirmation" in str(mock_template_engine.render_template.call_args).lower()

    @pytest.mark.asyncio
    async def test_send_password_reset_email_success(
        self, mock_user, mock_template_engine, mock_smtp_sender, mock_retry_service
    ):
        """Test sending password reset email"""
        service = EmailNotificationService(
            template_engine=mock_template_engine,
            sender=mock_smtp_sender,
            retry_service=mock_retry_service,
        )

        result = await service.send_password_reset_email(
            mock_user, reset_token="reset_token_456"
        )

        assert result is True
        mock_template_engine.render_template.assert_called_once()
        # Check that template was called with "password_reset"
        assert "password_reset" in str(
            mock_template_engine.render_template.call_args
        ).lower()

    @pytest.mark.asyncio
    @patch("app.services.email_notifications.settings")
    async def test_send_welcome_email_disabled(
        self, mock_settings, mock_user, mock_template_engine, mock_smtp_sender, mock_retry_service
    ):
        """Test that welcome email is not sent when disabled"""
        mock_settings.send_welcome_email = False

        service = EmailNotificationService(
            template_engine=mock_template_engine,
            sender=mock_smtp_sender,
            retry_service=mock_retry_service,
        )

        result = await service.send_welcome_email(mock_user, background=False)

        assert result is True
        # Template should not be rendered when feature is disabled
        mock_template_engine.render_template.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.email_notifications.settings")
    async def test_send_confirmation_email_disabled(
        self, mock_settings, mock_user, mock_template_engine, mock_smtp_sender, mock_retry_service
    ):
        """Test that confirmation email is not sent when disabled"""
        mock_settings.require_email_confirmation = False

        service = EmailNotificationService(
            template_engine=mock_template_engine,
            sender=mock_smtp_sender,
            retry_service=mock_retry_service,
        )

        result = await service.send_confirmation_email(
            mock_user, token="test_token", background=False
        )

        assert result is True
        mock_template_engine.render_template.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_welcome_email_background_task(
        self, mock_user, mock_template_engine, mock_smtp_sender, mock_retry_service
    ):
        """Test that welcome email can be sent as background task"""
        service = EmailNotificationService(
            template_engine=mock_template_engine,
            sender=mock_smtp_sender,
            retry_service=mock_retry_service,
        )

        # Send as background task
        result = await service.send_welcome_email(mock_user, background=True)

        assert result is True
        # Background task is scheduled but we don't wait for it
        # Just verify the method returns True for queuing

    @pytest.mark.asyncio
    async def test_service_initialization_with_defaults(self):
        """Test service initialization with default dependencies"""
        service = EmailNotificationService()

        assert service.template_engine is not None
        assert service.sender is not None
        assert service.retry_service is not None

    @pytest.mark.asyncio
    async def test_send_multiple_emails_sequential(
        self, mock_user, mock_template_engine, mock_smtp_sender, mock_retry_service
    ):
        """Test sending multiple emails sequentially"""
        service = EmailNotificationService(
            template_engine=mock_template_engine,
            sender=mock_smtp_sender,
            retry_service=mock_retry_service,
        )

        # Reset mock to count calls
        mock_template_engine.reset_mock()

        # Send welcome
        result1 = await service.send_welcome_email(mock_user, background=False)
        # Send confirmation
        result2 = await service.send_confirmation_email(
            mock_user, token="token", background=False
        )

        assert result1 is True
        assert result2 is True
        assert mock_template_engine.render_template.call_count == 2
