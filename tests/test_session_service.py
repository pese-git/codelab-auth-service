"""Tests for SessionService"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.refresh_token import RefreshToken
from app.services.session_service import SessionService


@pytest.fixture
def session_service():
    """Create SessionService instance"""
    return SessionService()


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


@pytest.fixture
def refresh_token_record():
    """Create a RefreshToken record"""
    return RefreshToken(
        id=str(uuid4()),
        jti_hash="abc123def456" * 5 + "abc",
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


class TestSessionService:
    """Test SessionService functionality"""

    @pytest.mark.asyncio
    async def test_list_user_sessions_success(
        self, session_service, mock_db, refresh_token_record
    ):
        """Test listing all active sessions for a user"""
        # Arrange
        session2 = RefreshToken(
            id=str(uuid4()),
            jti_hash="xyz789uvw012" * 5 + "xyz",
            user_id=refresh_token_record.user_id,
            client_id="ios_app",
            scope="read",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            session_id=str(uuid4()),
            created_at=datetime.now(timezone.utc) + timedelta(hours=1),
            ip_address="192.168.1.2",
            user_agent="Mobile Safari",
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(
            return_value=[refresh_token_record, session2]
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        sessions = await session_service.list_user_sessions(
            mock_db, refresh_token_record.user_id
        )

        # Assert
        assert len(sessions) == 2
        assert sessions[0]["client_id"] in ["web_app", "ios_app"]
        assert sessions[0]["session_id"] is not None
        assert sessions[0]["ip_address"] is not None
        assert "created_at" in sessions[0]

    @pytest.mark.asyncio
    async def test_list_user_sessions_empty(
        self, session_service, mock_db
    ):
        """Test list_user_sessions returns empty list when no sessions"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(return_value=[])
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        sessions = await session_service.list_user_sessions(
            mock_db, str(uuid4())
        )

        # Assert
        assert len(sessions) == 0

    @pytest.mark.asyncio
    async def test_list_user_sessions_groups_by_session_id(
        self, session_service, mock_db, refresh_token_record
    ):
        """Test that list_user_sessions groups tokens by session_id"""
        # Arrange - two tokens with same session_id (rotation)
        token2 = RefreshToken(
            id=str(uuid4()),
            jti_hash="token2123456" * 5 + "tok",
            user_id=refresh_token_record.user_id,
            client_id=refresh_token_record.client_id,
            scope="read",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            session_id=refresh_token_record.session_id,  # Same session
            created_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(
            return_value=[refresh_token_record, token2]
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        sessions = await session_service.list_user_sessions(
            mock_db, refresh_token_record.user_id
        )

        # Assert
        assert len(sessions) == 1  # Only one unique session
        assert sessions[0]["session_id"] == refresh_token_record.session_id

    @pytest.mark.asyncio
    async def test_list_user_sessions_keeps_latest_token(
        self, session_service, mock_db, refresh_token_record
    ):
        """Test that list keeps latest token per session"""
        # Arrange
        older_token = RefreshToken(
            id=str(uuid4()),
            jti_hash="older1234567" * 5 + "old",
            user_id=refresh_token_record.user_id,
            client_id="web_app",
            scope="read",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            session_id=refresh_token_record.session_id,
            created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(
            return_value=[older_token, refresh_token_record]
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        sessions = await session_service.list_user_sessions(
            mock_db, refresh_token_record.user_id
        )

        # Assert
        assert len(sessions) == 1
        assert sessions[0]["created_at"] == refresh_token_record.created_at

    @pytest.mark.asyncio
    async def test_list_user_sessions_sorted_by_created_at(
        self, session_service, mock_db, refresh_token_record
    ):
        """Test that sessions are sorted by created_at descending"""
        # Arrange
        session2 = RefreshToken(
            id=str(uuid4()),
            jti_hash="session2abcd" * 5 + "ses",
            user_id=refresh_token_record.user_id,
            client_id="ios_app",
            scope="read",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            session_id=str(uuid4()),
            created_at=datetime.now(timezone.utc) + timedelta(hours=2),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(
            return_value=[refresh_token_record, session2]
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        sessions = await session_service.list_user_sessions(
            mock_db, refresh_token_record.user_id
        )

        # Assert
        assert len(sessions) == 2
        assert sessions[0]["created_at"] > sessions[1]["created_at"]

    @pytest.mark.asyncio
    async def test_get_session_info_success(
        self, session_service, mock_db, refresh_token_record
    ):
        """Test getting detailed info for a specific session"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.first = MagicMock(
            return_value=refresh_token_record
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        info = await session_service.get_session_info(
            mock_db, refresh_token_record.user_id, refresh_token_record.session_id
        )

        # Assert
        assert info is not None
        assert info["session_id"] == refresh_token_record.session_id
        assert info["client_id"] == refresh_token_record.client_id
        assert info["scope"] == refresh_token_record.scope
        assert info["ip_address"] == refresh_token_record.ip_address
        assert info["user_agent"] == refresh_token_record.user_agent

    @pytest.mark.asyncio
    async def test_get_session_info_not_found(
        self, session_service, mock_db
    ):
        """Test get_session_info returns None if session not found"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.first = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        info = await session_service.get_session_info(
            mock_db, str(uuid4()), str(uuid4())
        )

        # Assert
        assert info is None

    @pytest.mark.asyncio
    async def test_revoke_session_success(
        self, session_service, mock_db, refresh_token_record
    ):
        """Test successful revocation of a session"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(
            return_value=[refresh_token_record]
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await session_service.revoke_session(
            mock_db, refresh_token_record.user_id, refresh_token_record.session_id
        )

        # Assert
        assert result is True
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_session_not_found(
        self, session_service, mock_db
    ):
        """Test revoke_session returns False if session not found"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(return_value=[])
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await session_service.revoke_session(
            mock_db, str(uuid4()), str(uuid4())
        )

        # Assert
        assert result is False
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_revoke_session_multiple_tokens(
        self, session_service, mock_db, refresh_token_record
    ):
        """Test revoke_session revokes all tokens in a session"""
        # Arrange
        token2 = RefreshToken(
            id=str(uuid4()),
            jti_hash="token2abcdef" * 5 + "tok",
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
        result = await session_service.revoke_session(
            mock_db, refresh_token_record.user_id, refresh_token_record.session_id
        )

        # Assert
        assert result is True
        assert refresh_token_record.revoked is True
        assert token2.revoked is True

    @pytest.mark.asyncio
    async def test_revoke_all_sessions_success(
        self, session_service, mock_db, refresh_token_record
    ):
        """Test revoking all sessions for a user"""
        # Arrange
        session2 = RefreshToken(
            id=str(uuid4()),
            jti_hash="session2efgh" * 5 + "ses",
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
        count = await session_service.revoke_all_sessions(
            mock_db, refresh_token_record.user_id
        )

        # Assert
        assert count == 2
        assert refresh_token_record.revoked is True
        assert session2.revoked is True
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_all_sessions_no_sessions(
        self, session_service, mock_db
    ):
        """Test revoke_all_sessions returns 0 if no sessions"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(return_value=[])
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        count = await session_service.revoke_all_sessions(
            mock_db, str(uuid4())
        )

        # Assert
        assert count == 0
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_revoke_all_sessions_except_one(
        self, session_service, mock_db, refresh_token_record
    ):
        """Test revoke_all_sessions with except_session_id"""
        # Arrange
        keep_session_id = refresh_token_record.session_id
        session2 = RefreshToken(
            id=str(uuid4()),
            jti_hash="session2ijkl" * 5 + "ses",
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
        count = await session_service.revoke_all_sessions(
            mock_db, refresh_token_record.user_id, except_session_id=keep_session_id
        )

        # Assert
        assert count == 1
        assert refresh_token_record.revoked is False  # Kept active
        assert session2.revoked is True  # Revoked

    @pytest.mark.asyncio
    async def test_revoke_all_sessions_timestamps(
        self, session_service, mock_db, refresh_token_record
    ):
        """Test that revoke_all_sessions sets revoked_at timestamps"""
        # Arrange
        before_revoke = datetime.now(timezone.utc)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(
            return_value=[refresh_token_record]
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        count = await session_service.revoke_all_sessions(
            mock_db, refresh_token_record.user_id
        )

        # Assert
        assert count == 1
        assert refresh_token_record.revoked is True
        assert refresh_token_record.revoked_at is not None
        assert refresh_token_record.revoked_at >= before_revoke

    @pytest.mark.asyncio
    async def test_get_active_sessions_count_success(
        self, session_service, mock_db, refresh_token_record
    ):
        """Test getting count of active sessions"""
        # Arrange
        session2 = RefreshToken(
            id=str(uuid4()),
            jti_hash="session2mnop" * 5 + "ses",
            user_id=refresh_token_record.user_id,
            client_id="ios_app",
            scope="read",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            session_id=str(uuid4()),
            created_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(
            return_value=[refresh_token_record, session2]
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        count = await session_service.get_active_sessions_count(
            mock_db, refresh_token_record.user_id
        )

        # Assert
        assert count == 2

    @pytest.mark.asyncio
    async def test_get_active_sessions_count_no_sessions(
        self, session_service, mock_db
    ):
        """Test get_active_sessions_count returns 0 if no sessions"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(return_value=[])
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        count = await session_service.get_active_sessions_count(
            mock_db, str(uuid4())
        )

        # Assert
        assert count == 0

    @pytest.mark.asyncio
    async def test_session_info_contains_all_fields(
        self, session_service, mock_db, refresh_token_record
    ):
        """Test that session info includes all required fields"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.first = MagicMock(
            return_value=refresh_token_record
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        info = await session_service.get_session_info(
            mock_db, refresh_token_record.user_id, refresh_token_record.session_id
        )

        # Assert
        required_fields = [
            "session_id", "client_id", "scope", "created_at",
            "last_used", "last_rotated_at", "ip_address", "user_agent", "expires_at"
        ]
        for field in required_fields:
            assert field in info
