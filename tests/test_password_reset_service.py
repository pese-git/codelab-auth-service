"""Tests for password reset service"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.password_reset_token import PasswordResetToken
from app.services.password_reset_service import (
    TOKEN_EXPIRATION_MINUTES,
    PasswordResetService,
)
from tests.conftest import MockUser


@pytest.fixture
def password_reset_service():
    """Create password reset service instance"""
    return PasswordResetService()


@pytest.fixture
def mock_user():
    """Create mock user for testing"""
    return MockUser(
        id=str(uuid4()),
        username="testuser",
        email="testuser@example.com",
        password_hash="hashed_password",
        email_confirmed=False,
    )


@pytest.fixture
async def mock_db():
    """Create mock database session"""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    db.execute = AsyncMock()
    db.delete = AsyncMock()
    return db


class TestPasswordResetService:
    """Test password reset service functionality"""

    @pytest.mark.asyncio
    async def test_create_reset_token_success(
        self, password_reset_service, mock_user, mock_db
    ):
        """Test successful creation of password reset token.
        
        Verifies that:
        - Token is generated as a non-empty string
        - Token is added to database
        - Token expiration is set to current time + 30 minutes
        """
        # Arrange
        before_time = datetime.now(UTC)
        
        # Act
        token = await password_reset_service.create_token(mock_db, mock_user.id)
        
        # Assert
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token was added to database
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        
        # Verify token record structure
        added_token = mock_db.add.call_args[0][0]
        assert isinstance(added_token, PasswordResetToken)
        assert added_token.user_id == mock_user.id
        assert added_token.token_hash is not None
        assert len(added_token.token_hash) == 64  # SHA-256 hex digest
        
        # Verify expiration is 30 minutes from now
        expiration_delta = added_token.expires_at - before_time
        expected_delta = timedelta(minutes=TOKEN_EXPIRATION_MINUTES)
        assert expiration_delta >= expected_delta - timedelta(seconds=1)
        assert expiration_delta <= expected_delta + timedelta(seconds=5)

    @pytest.mark.asyncio
    async def test_create_reset_token_generates_unique_tokens(
        self, password_reset_service, mock_user, mock_db
    ):
        """Test that consecutive token creations generate different tokens.
        
        Verifies cryptographic uniqueness of token generation.
        """
        # Arrange & Act
        token1 = await password_reset_service.create_token(mock_db, mock_user.id)
        token2 = await password_reset_service.create_token(mock_db, mock_user.id)
        
        # Assert
        assert token1 != token2
        assert len(token1) > 0
        assert len(token2) > 0

    @pytest.mark.asyncio
    async def test_verify_valid_token_success(
        self, password_reset_service, mock_user, mock_db
    ):
        """Test successful verification of a valid token.
        
        Verifies that:
        - Valid token returns user ID
        - Token hash matches stored hash
        - Token is not expired
        - Token is not marked as used
        """
        # Arrange
        token = "test_token_valid_xyz"
        token_hash = password_reset_service._hash_token(token)
        
        # Create token record in database
        reset_token = PasswordResetToken(
            user_id=mock_user.id,
            token_hash=token_hash,
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
            used_at=None,
        )
        
        # Mock database query to return the token
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=reset_token)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Act
        user_id = await password_reset_service.verify_token(mock_db, token)
        
        # Assert
        assert user_id == mock_user.id

    @pytest.mark.asyncio
    async def test_verify_expired_token_returns_none(
        self, password_reset_service, mock_user, mock_db
    ):
        """Test that expired tokens are rejected.
        
        Verifies that:
        - Expired token returns None
        - is_expired() check is working
        """
        # Arrange
        token = "expired_token_string"
        token_hash = password_reset_service._hash_token(token)
        
        # Create expired token record
        reset_token = PasswordResetToken(
            user_id=mock_user.id,
            token_hash=token_hash,
            created_at=datetime.now(UTC) - timedelta(minutes=35),
            expires_at=datetime.now(UTC) - timedelta(minutes=5),
            used_at=None,
        )
        
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=reset_token)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Act
        user_id = await password_reset_service.verify_token(mock_db, token)
        
        # Assert
        assert user_id is None

    @pytest.mark.asyncio
    async def test_verify_used_token_returns_none(
        self, password_reset_service, mock_user, mock_db
    ):
        """Test that already-used tokens are rejected.
        
        Verifies that:
        - Used token returns None
        - is_used() check is working
        """
        # Arrange
        token = "used_token_string"
        token_hash = password_reset_service._hash_token(token)
        
        # Create used token record
        reset_token = PasswordResetToken(
            user_id=mock_user.id,
            token_hash=token_hash,
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
            used_at=datetime.now(UTC),  # Mark as used
        )
        
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=reset_token)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Act
        user_id = await password_reset_service.verify_token(mock_db, token)
        
        # Assert
        assert user_id is None

    @pytest.mark.asyncio
    async def test_verify_invalid_token_returns_none(
        self, password_reset_service, mock_db
    ):
        """Test that invalid tokens are rejected.
        
        Verifies that:
        - Non-existent token returns None
        - Database query returns None
        """
        # Arrange
        invalid_token = "this_token_does_not_exist"
        
        # Mock database query returning no result
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Act
        user_id = await password_reset_service.verify_token(mock_db, invalid_token)
        
        # Assert
        assert user_id is None

    @pytest.mark.asyncio
    async def test_verify_empty_token_returns_none(
        self, password_reset_service, mock_db
    ):
        """Test that empty or None tokens are rejected.
        
        Verifies early return for invalid input.
        """
        # Act & Assert
        assert await password_reset_service.verify_token(mock_db, "") is None
        assert await password_reset_service.verify_token(mock_db, None) is None

    @pytest.mark.asyncio
    async def test_mark_token_used_success(
        self, password_reset_service, mock_user, mock_db
    ):
        """Test successful marking of token as used.
        
        Verifies that:
        - Token is marked with used_at timestamp
        - Database is committed
        - Function returns True
        """
        # Arrange
        token = "mark_token_string"
        token_hash = password_reset_service._hash_token(token)
        
        # Create token record
        reset_token = PasswordResetToken(
            user_id=mock_user.id,
            token_hash=token_hash,
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
            used_at=None,
        )
        
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=reset_token)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        before_time = datetime.now(UTC)
        
        # Act
        result = await password_reset_service.mark_token_used(mock_db, token)
        
        after_time = datetime.now(UTC)
        
        # Assert
        assert result is True
        assert reset_token.used_at is not None
        assert reset_token.used_at >= before_time
        assert reset_token.used_at <= after_time
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_token_used_invalid_token_returns_false(
        self, password_reset_service, mock_db
    ):
        """Test marking non-existent token as used returns False.
        
        Verifies graceful handling of invalid tokens.
        """
        # Arrange
        invalid_token = "this_token_does_not_exist"
        
        # Mock database query returning no result
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Act
        result = await password_reset_service.mark_token_used(mock_db, invalid_token)
        
        # Assert
        assert result is False
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens(
        self, password_reset_service, mock_user, mock_db
    ):
        """Test cleanup of expired password reset tokens.
        
        Verifies that:
        - Expired tokens are deleted
        - Count of deleted tokens is returned
        - Database is committed
        """
        # Arrange
        now = datetime.now(UTC)
        
        # Create expired token records
        expired_token1 = PasswordResetToken(
            user_id=str(uuid4()),
            token_hash="hash1",
            created_at=now - timedelta(minutes=60),
            expires_at=now - timedelta(minutes=30),
        )
        expired_token2 = PasswordResetToken(
            user_id=str(uuid4()),
            token_hash="hash2",
            created_at=now - timedelta(minutes=60),
            expires_at=now - timedelta(minutes=30),
        )
        
        # Mock database query
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [expired_token1, expired_token2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Act
        deleted_count = await password_reset_service.cleanup_expired_tokens(
            mock_db
        )
        
        # Assert
        assert deleted_count == 2
        assert mock_db.delete.call_count == 2
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_no_expired_tokens(
        self, password_reset_service, mock_db
    ):
        """Test cleanup when no expired tokens exist.
        
        Verifies graceful handling when there's nothing to delete.
        """
        # Arrange
        # Mock database query returning empty list
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Act
        deleted_count = await password_reset_service.cleanup_expired_tokens(
            mock_db
        )
        
        # Assert
        assert deleted_count == 0
        mock_db.delete.assert_not_called()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_hash_token_consistency(
        self, password_reset_service
    ):
        """Test that token hashing is consistent.
        
        Verifies that:
        - Same token produces same hash
        - Hash is SHA-256 (64 hex characters)
        - Hash is deterministic
        """
        # Arrange
        token = "test_token_string"
        
        # Act
        hash1 = password_reset_service._hash_token(token)
        hash2 = password_reset_service._hash_token(token)
        
        # Assert
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest length
        assert isinstance(hash1, str)

    @pytest.mark.asyncio
    async def test_hash_token_different_for_different_inputs(
        self, password_reset_service
    ):
        """Test that different tokens produce different hashes.
        
        Verifies cryptographic uniqueness.
        """
        # Arrange
        token1 = "token_one"
        token2 = "token_two"
        
        # Act
        hash1 = password_reset_service._hash_token(token1)
        hash2 = password_reset_service._hash_token(token2)
        
        # Assert
        assert hash1 != hash2
