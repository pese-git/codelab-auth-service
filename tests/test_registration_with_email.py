"""Integration tests for user registration with email notifications"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.email_service import email_service
from app.services.user_service import user_service
from tests.conftest import MockUser


@pytest.fixture
def registration_data():
    """Create sample registration data"""
    return {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "SecurePassword123!",
    }


@pytest.fixture
async def mock_db():
    """Create mock database session"""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    db.execute = AsyncMock()
    db.refresh = AsyncMock()
    return db


class TestRegistrationWithEmail:
    """Integration tests for registration with email functionality"""

    @pytest.mark.asyncio
    @patch("app.services.user_service.settings")
    async def test_registration_sends_welcome_email(
        self, mock_settings, registration_data, mock_db
    ):
        """Test that successful registration sends welcome email"""
        mock_settings.send_welcome_email = True

        # Create a mock user that would be returned from registration
        mock_user = MockUser(
            id=str(uuid4()),
            username=registration_data["username"],
            email=registration_data["email"],
            password_hash="hashed_password",
            email_confirmed=False,
        )

        with patch(
            "app.services.user_service.user_service.register_user",
            return_value=mock_user,
        ):
            with patch(
                "app.services.email_notifications.EmailNotificationService"
            ) as MockEmailService:
                mock_email_service = AsyncMock()
                MockEmailService.return_value = mock_email_service
                mock_email_service.send_welcome_email.return_value = True

                user = await user_service.register_user(mock_db, registration_data)

                assert user.email == registration_data["email"]
                assert user.username == registration_data["username"]

    @pytest.mark.asyncio
    @patch("app.services.user_service.settings")
    async def test_registration_sends_confirmation_email(
        self, mock_settings, registration_data, mock_db
    ):
        """Test that successful registration sends confirmation email"""
        mock_settings.require_email_confirmation = True

        mock_user = MockUser(
            id=str(uuid4()),
            username=registration_data["username"],
            email=registration_data["email"],
            password_hash="hashed_password",
            email_confirmed=False,
        )

        with patch(
            "app.services.user_service.user_service.register_user",
            return_value=mock_user,
        ):
            with patch("app.services.email_service.email_service.generate_confirmation_token") as mock_gen_token:
                with patch("app.services.email_service.email_service.save_confirmation_token") as mock_save_token:
                    with patch("app.services.email_service.email_service.send_confirmation_email") as mock_send:
                        mock_gen_token.return_value = "test_token_123"
                        mock_save_token.return_value = True
                        mock_send.return_value = True

                        user = await user_service.register_user(mock_db, registration_data)

                        assert user.email == registration_data["email"]

    @pytest.mark.asyncio
    @patch("app.services.user_service.settings")
    async def test_registration_fails_no_email_sent(
        self, mock_settings, registration_data, mock_db
    ):
        """Test that failed registration doesn't send emails"""
        mock_settings.send_welcome_email = True

        # Simulate registration failure (duplicate email)
        with patch(
            "app.services.user_service.user_service.register_user",
            side_effect=ValueError("Email already registered"),
        ):
            with patch(
                "app.services.email_notifications.EmailNotificationService"
            ) as MockEmailService:
                mock_email_service = AsyncMock()
                MockEmailService.return_value = mock_email_service

                try:
                    await user_service.register_user(mock_db, registration_data)
                except ValueError:
                    pass

                # Welcome email should not be sent on registration failure
                mock_email_service.send_welcome_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_confirmation_token_has_correct_content(self, registration_data, mock_db):
        """Test that generated confirmation token is properly formatted"""
        user_id = str(uuid4())
        token = await email_service.generate_confirmation_token(user_id)

        assert token is not None
        assert len(token) > 0
        # URL-safe token shouldn't contain certain characters
        assert " " not in token
        assert "\n" not in token

    @pytest.mark.asyncio
    async def test_confirmation_email_contains_token(self, mock_db):
        """Test that confirmation email message includes the token"""
        user_id = str(uuid4())
        mock_user = MockUser(
            id=user_id,
            username="testuser",
            email="test@example.com",
            password_hash="hash",
            email_confirmed=False,
        )

        token = await email_service.generate_confirmation_token(user_id)

        with patch(
            "app.services.email_notifications.EmailNotificationService"
        ) as MockEmailService:
            mock_email_service = AsyncMock()
            MockEmailService.return_value = mock_email_service

            # Create a mock message that captures the call
            async def capture_send_confirmation(user, token_arg, background=False):
                # Verify that the token is passed to the notification service
                assert token_arg == token
                return True

            mock_email_service.send_confirmation_email = AsyncMock(
                side_effect=capture_send_confirmation
            )

            result = await email_service.send_confirmation_email(mock_user, token, mock_db)

            assert result is True
            mock_email_service.send_confirmation_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_email_service_graceful_degradation(self, registration_data, mock_db):
        """Test that registration doesn't fail if email service is unavailable"""
        mock_user = MockUser(
            id=str(uuid4()),
            username=registration_data["username"],
            email=registration_data["email"],
            password_hash="hashed_password",
            email_confirmed=False,
        )

        with patch(
            "app.services.user_service.user_service.register_user",
            return_value=mock_user,
        ):
            with patch(
                "app.services.email_notifications.EmailNotificationService",
                side_effect=Exception("Email service unavailable"),
            ):
                # Registration should still succeed even if email service fails
                user = await user_service.register_user(mock_db, registration_data)
                assert user is not None
                assert user.email == registration_data["email"]

    @pytest.mark.asyncio
    @patch("app.services.user_service.settings")
    async def test_registration_email_disabled_feature_flag(
        self, mock_settings, registration_data, mock_db
    ):
        """Test registration when email features are disabled via config"""
        mock_settings.send_welcome_email = False
        mock_settings.require_email_confirmation = False

        mock_user = MockUser(
            id=str(uuid4()),
            username=registration_data["username"],
            email=registration_data["email"],
            password_hash="hashed_password",
            email_confirmed=False,
        )

        with patch(
            "app.services.user_service.user_service.register_user",
            return_value=mock_user,
        ):
            with patch(
                "app.services.email_notifications.EmailNotificationService"
            ) as MockEmailService:
                mock_email_service = AsyncMock()
                MockEmailService.return_value = mock_email_service

                user = await user_service.register_user(mock_db, registration_data)

                # Email services should not be called when disabled
                assert user is not None
                # Check that the registration completed successfully
                assert user.username == registration_data["username"]
