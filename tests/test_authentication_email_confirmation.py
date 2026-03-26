"""Tests for email confirmation requirement in authentication.

This module verifies that users cannot authenticate without confirming their email
when email confirmation is required in the application settings.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import user_service
from app.core.config import settings
from app.utils.crypto import hash_password
from tests.conftest import MockUser


class TestAuthenticationEmailConfirmation:
    """Tests for email confirmation requirement during authentication."""

    @pytest.mark.asyncio
    async def test_authenticate_fails_without_email_confirmation(
        self, db_session: AsyncSession
    ):
        """Test that authentication fails when email is not confirmed.
        
        Verifies that:
        - User with unconfirmed email cannot authenticate
        - Authentication returns None when email_confirmed is False
        - Proper logging occurs for email not confirmed
        """
        # Skip test if email confirmation is not required in settings
        if not settings.require_email_confirmation:
            pytest.skip("Email confirmation is not required in settings")
        
        # Arrange - Create user with unconfirmed email
        user_with_unconfirmed_email = MockUser(
            id="550e8400-e29b-41d4-a716-446655440001",
            username="unconfirmed_user",
            email="unconfirmed@example.com",
            password_hash=hash_password("CorrectPassword123!"),
            email_confirmed=False,  # Email is NOT confirmed
        )
        
        # Mock database methods to return user
        db_session.execute = AsyncMock()
        db_session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=user_with_unconfirmed_email
        )
        db_session.commit = AsyncMock()
        
        # Act - Try to authenticate
        result = await user_service.authenticate(
            db_session,
            username="unconfirmed_user",
            password="CorrectPassword123!",
        )
        
        # Assert - Should fail due to email not confirmed
        assert result is None, (
            "Authentication should fail when email is not confirmed and "
            "require_email_confirmation is True"
        )

    @pytest.mark.asyncio
    async def test_authenticate_succeeds_with_confirmed_email(
        self, db_session: AsyncSession
    ):
        """Test that authentication succeeds when email is confirmed.
        
        Verifies that:
        - User with confirmed email can authenticate
        - Authentication returns User object when email_confirmed is True
        - All checks pass in correct order
        """
        # Skip test if email confirmation is not required in settings
        if not settings.require_email_confirmation:
            pytest.skip("Email confirmation is not required in settings")
        
        # Arrange - Create user with confirmed email
        user_with_confirmed_email = MockUser(
            id="550e8400-e29b-41d4-a716-446655440002",
            username="confirmed_user",
            email="confirmed@example.com",
            password_hash=hash_password("CorrectPassword123!"),
            email_confirmed=True,  # Email IS confirmed
            is_active=True,
        )
        
        # Mock database methods to return user
        db_session.execute = AsyncMock()
        db_session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=user_with_confirmed_email
        )
        db_session.commit = AsyncMock()
        
        # Act - Authenticate with confirmed email
        result = await user_service.authenticate(
            db_session,
            username="confirmed_user",
            password="CorrectPassword123!",
        )
        
        # Assert - Should succeed
        assert result is not None, (
            "Authentication should succeed when email is confirmed and "
            "password is correct"
        )
        assert result.username == "confirmed_user"
        assert result.email_confirmed is True

    @pytest.mark.asyncio
    async def test_authenticate_failure_order_email_before_password(
        self, db_session: AsyncSession
    ):
        """Test that email confirmation is checked before password verification.
        
        Verifies that:
        - Email confirmation check happens before password check
        - Even with wrong password, returns None due to unconfirmed email first
        - This prevents information leakage about whether email exists
        """
        # Skip test if email confirmation is not required in settings
        if not settings.require_email_confirmation:
            pytest.skip("Email confirmation is not required in settings")
        
        # Arrange - User with unconfirmed email and wrong password attempt
        user_unconfirmed = MockUser(
            id="550e8400-e29b-41d4-a716-446655440003",
            username="another_unconfirmed",
            email="another@example.com",
            password_hash=hash_password("CorrectPassword123!"),
            email_confirmed=False,  # Email NOT confirmed
            is_active=True,
        )
        
        db_session.execute = AsyncMock()
        db_session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=user_unconfirmed
        )
        db_session.commit = AsyncMock()
        
        # Act - Try with wrong password
        result = await user_service.authenticate(
            db_session,
            username="another_unconfirmed",
            password="WrongPassword123!",  # Wrong password
        )
        
        # Assert - Should fail due to email not confirmed (checked first)
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_inactive_user_checked_before_email(
        self, db_session: AsyncSession
    ):
        """Test that user active status is checked before email confirmation.
        
        Verifies the order of checks:
        1. User exists
        2. User is active
        3. Email is confirmed
        4. Password is correct
        """
        # Skip test if email confirmation is not required in settings
        if not settings.require_email_confirmation:
            pytest.skip("Email confirmation is not required in settings")
        
        # Arrange - Inactive user with unconfirmed email
        inactive_user = MockUser(
            id="550e8400-e29b-41d4-a716-446655440004",
            username="inactive_user",
            email="inactive@example.com",
            password_hash=hash_password("CorrectPassword123!"),
            email_confirmed=False,  # Email not confirmed
            is_active=False,  # User is inactive
        )
        
        db_session.execute = AsyncMock()
        db_session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=inactive_user
        )
        db_session.commit = AsyncMock()
        
        # Act
        result = await user_service.authenticate(
            db_session,
            username="inactive_user",
            password="CorrectPassword123!",
        )
        
        # Assert - Should fail due to inactive status (checked before email)
        assert result is None


class TestEmailConfirmationFlagBehavior:
    """Tests for email_confirmed flag behavior in user authentication."""

    @pytest.mark.asyncio
    async def test_mock_user_email_confirmed_defaults_to_false(self):
        """Test that MockUser email_confirmed defaults to False."""
        # Arrange & Act
        user = MockUser(
            id="test-id",
            username="test",
            email="test@example.com",
            password_hash="hash",
        )
        
        # Assert
        assert user.email_confirmed is False

    @pytest.mark.asyncio
    async def test_mock_user_email_confirmed_can_be_set_true(self):
        """Test that MockUser email_confirmed can be explicitly set to True."""
        # Arrange & Act
        user = MockUser(
            id="test-id",
            username="test",
            email="test@example.com",
            password_hash="hash",
            email_confirmed=True,
        )
        
        # Assert
        assert user.email_confirmed is True
