"""Tests for RefreshTokenService"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.refresh_token import RefreshToken
from app.schemas.token import RefreshTokenPayload
from app.services.refresh_token_service import RefreshTokenService


@pytest.fixture
def refresh_token_service():
    """Create RefreshTokenService instance"""
    return RefreshTokenService()


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
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def refresh_token_payload():
    """Create a refresh token payload"""
    now = datetime.now(timezone.utc)
    return RefreshTokenPayload(
        iss="auth_server",
        sub=str(uuid4()),
        aud="web_app",
        client_id="web_app",
        scope="read write",
        jti=str(uuid4()),
        iat=int(now.timestamp()),
        nbf=int(now.timestamp()),
        exp=int((now + timedelta(days=30)).timestamp()),
    )


@pytest.fixture
def refresh_token_record():
    """Create a RefreshToken record"""
    return RefreshToken(
        id=str(uuid4()),
        jti_hash="abc123def456" * 5 + "abc",  # 64 chars
        user_id=str(uuid4()),
        client_id="web_app",
        scope="read write",
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        revoked=False,
        revoked_at=None,
        parent_jti_hash=None,
        session_id=str(uuid4()),
        last_used=datetime.now(timezone.utc),
        last_rotated_at=datetime.now(timezone.utc),
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        created_at=datetime.now(timezone.utc),
    )


class TestRefreshTokenService:
    """Test RefreshTokenService functionality"""

    @pytest.mark.asyncio
    async def test_save_refresh_token_success(
        self, refresh_token_service, mock_db, refresh_token_payload
    ):
        """Test successful save of refresh token"""
        # Arrange
        session_id = str(uuid4())
        ip_address = "192.168.1.1"
        user_agent = "Mozilla/5.0"

        # Mock db.refresh to return a token
        token_record = RefreshToken(
            id=str(uuid4()),
            jti_hash="abc123def456" * 5 + "abc",
            user_id=refresh_token_payload.sub,
            client_id=refresh_token_payload.client_id,
            scope=refresh_token_payload.scope,
            expires_at=datetime.fromtimestamp(
                refresh_token_payload.exp, tz=timezone.utc
            ),
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            parent_jti_hash=None,
        )
        mock_db.refresh = AsyncMock()

        # Act
        result = await refresh_token_service.save_refresh_token(
            mock_db,
            refresh_token_payload,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Assert
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_save_refresh_token_generates_session_id_if_not_provided(
        self, refresh_token_service, mock_db, refresh_token_payload
    ):
        """Test that session_id is generated if not provided"""
        # Act
        result = await refresh_token_service.save_refresh_token(
            mock_db, refresh_token_payload
        )

        # Assert
        mock_db.add.assert_called_once()
        added_token = mock_db.add.call_args[0][0]
        assert added_token.session_id is not None

    @pytest.mark.asyncio
    async def test_save_refresh_token_with_parent_jti(
        self, refresh_token_service, mock_db, refresh_token_payload
    ):
        """Test save with parent JTI for token rotation chain"""
        # Arrange
        parent_jti = str(uuid4())

        # Act
        result = await refresh_token_service.save_refresh_token(
            mock_db, refresh_token_payload, parent_jti=parent_jti
        )

        # Assert
        mock_db.add.assert_called_once()
        added_token = mock_db.add.call_args[0][0]
        assert added_token.parent_jti_hash is not None

    @pytest.mark.asyncio
    async def test_get_by_jti_success(
        self, refresh_token_service, mock_db, refresh_token_record
    ):
        """Test getting refresh token by JTI"""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=refresh_token_record)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await refresh_token_service.get_by_jti(
            mock_db, "test_jti"
        )

        # Assert
        assert result == refresh_token_record

    @pytest.mark.asyncio
    async def test_get_by_jti_not_found(
        self, refresh_token_service, mock_db
    ):
        """Test get_by_jti returns None if token not found"""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await refresh_token_service.get_by_jti(
            mock_db, "nonexistent_jti"
        )

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_refresh_token_valid(
        self, refresh_token_service, mock_db, refresh_token_record
    ):
        """Test validation of valid refresh token"""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=refresh_token_record)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        is_valid, error = await refresh_token_service.validate_refresh_token(
            mock_db, "test_jti"
        )

        # Assert
        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_refresh_token_not_found(
        self, refresh_token_service, mock_db
    ):
        """Test validation fails for nonexistent token"""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        is_valid, error = await refresh_token_service.validate_refresh_token(
            mock_db, "nonexistent_jti"
        )

        # Assert
        assert is_valid is False
        assert "not found" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_refresh_token_revoked(
        self, refresh_token_service, mock_db, refresh_token_record
    ):
        """Test validation fails for revoked token"""
        # Arrange
        refresh_token_record.revoked = True
        refresh_token_record.revoked_at = datetime.now(timezone.utc)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=refresh_token_record)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        is_valid, error = await refresh_token_service.validate_refresh_token(
            mock_db, "test_jti"
        )

        # Assert
        assert is_valid is False
        assert "revoked" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_refresh_token_expired(
        self, refresh_token_service, mock_db, refresh_token_record
    ):
        """Test validation fails for expired token"""
        # Arrange
        refresh_token_record.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=refresh_token_record)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        is_valid, error = await refresh_token_service.validate_refresh_token(
            mock_db, "test_jti"
        )

        # Assert
        assert is_valid is False
        assert "expired" in error.lower()

    @pytest.mark.asyncio
    async def test_revoke_token_success(
        self, refresh_token_service, mock_db, refresh_token_record
    ):
        """Test successful token revocation"""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=refresh_token_record)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await refresh_token_service.revoke_token(
            mock_db, "test_jti"
        )

        # Assert
        assert result is True
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_token_not_found(
        self, refresh_token_service, mock_db
    ):
        """Test revoke_token returns False if token not found"""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await refresh_token_service.revoke_token(
            mock_db, "nonexistent_jti"
        )

        # Assert
        assert result is False
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_revoke_token_chain(
        self, refresh_token_service, mock_db, refresh_token_record
    ):
        """Test revocation of entire token chain"""
        # Arrange
        token2 = RefreshToken(
            id=str(uuid4()),
            jti_hash="xyz789uvw012" * 5 + "xyz",
            user_id=refresh_token_record.user_id,
            client_id=refresh_token_record.client_id,
            scope="read write",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            revoked_at=None,
            parent_jti_hash=refresh_token_record.jti_hash,
            session_id=refresh_token_record.session_id,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(
            return_value=[refresh_token_record, token2]
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        await refresh_token_service.revoke_token_chain(
            mock_db, refresh_token_record
        )

        # Assert
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens(
        self, refresh_token_service, mock_db
    ):
        """Test cleanup of expired tokens"""
        # Arrange
        expired_token = RefreshToken(
            id=str(uuid4()),
            jti_hash="expired123456" * 4 + "exp",
            user_id=str(uuid4()),
            client_id="web_app",
            scope="read",
            expires_at=datetime.now(timezone.utc) - timedelta(days=30),
            revoked=False,
            session_id=str(uuid4()),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(
            return_value=[expired_token]
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        count = await refresh_token_service.cleanup_expired_tokens(
            mock_db, days_to_keep=7
        )

        # Assert
        assert count == 1
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens_no_tokens(
        self, refresh_token_service, mock_db
    ):
        """Test cleanup when no expired tokens exist"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(return_value=[])
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        count = await refresh_token_service.cleanup_expired_tokens(
            mock_db, days_to_keep=7
        )

        # Assert
        assert count == 0
        mock_db.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_revoke_session(
        self, refresh_token_service, mock_db, refresh_token_record
    ):
        """Test revocation of all tokens in a session"""
        # Arrange
        token2 = RefreshToken(
            id=str(uuid4()),
            jti_hash="token2123456789" * 4,
            user_id=refresh_token_record.user_id,
            client_id=refresh_token_record.client_id,
            scope="read",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            session_id=refresh_token_record.session_id,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(
            return_value=[refresh_token_record, token2]
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await refresh_token_service.revoke_session(
            mock_db, refresh_token_record.user_id, refresh_token_record.session_id
        )

        # Assert
        assert result is True
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_session_no_tokens(
        self, refresh_token_service, mock_db
    ):
        """Test revoke_session returns False if no tokens found"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(return_value=[])
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await refresh_token_service.revoke_session(
            mock_db, str(uuid4()), str(uuid4())
        )

        # Assert
        assert result is False
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_user_sessions(
        self, refresh_token_service, mock_db, refresh_token_record
    ):
        """Test getting all active sessions for a user"""
        # Arrange
        session2 = RefreshToken(
            id=str(uuid4()),
            jti_hash="session2123456" * 4,
            user_id=refresh_token_record.user_id,
            client_id="ios_app",
            scope="read",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            session_id=str(uuid4()),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(
            return_value=[refresh_token_record, session2]
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        sessions = await refresh_token_service.get_user_sessions(
            mock_db, refresh_token_record.user_id
        )

        # Assert
        assert len(sessions) == 2
        assert sessions[0].session_id != sessions[1].session_id

    @pytest.mark.asyncio
    async def test_get_user_sessions_no_sessions(
        self, refresh_token_service, mock_db
    ):
        """Test get_user_sessions returns empty list if no sessions"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(return_value=[])
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        sessions = await refresh_token_service.get_user_sessions(
            mock_db, str(uuid4())
        )

        # Assert
        assert len(sessions) == 0

    @pytest.mark.asyncio
    async def test_get_session_metadata_success(
        self, refresh_token_service, mock_db, refresh_token_record
    ):
        """Test getting metadata for a specific session"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.first = MagicMock(
            return_value=refresh_token_record
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        metadata = await refresh_token_service.get_session_metadata(
            mock_db, refresh_token_record.user_id, refresh_token_record.session_id
        )

        # Assert
        assert metadata is not None
        assert metadata["session_id"] == refresh_token_record.session_id
        assert metadata["client_id"] == refresh_token_record.client_id
        assert metadata["ip_address"] == refresh_token_record.ip_address

    @pytest.mark.asyncio
    async def test_get_session_metadata_not_found(
        self, refresh_token_service, mock_db
    ):
        """Test get_session_metadata returns None if session not found"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.first = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        metadata = await refresh_token_service.get_session_metadata(
            mock_db, str(uuid4()), str(uuid4())
        )

        # Assert
        assert metadata is None
