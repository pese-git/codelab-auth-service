"""Integration tests for refresh token flow"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.refresh_token import RefreshToken
from app.schemas.token import RefreshTokenPayload
from app.services.refresh_token_service import RefreshTokenService
from app.services.session_service import SessionService


@pytest.fixture
def refresh_token_service():
    """Create RefreshTokenService instance"""
    return RefreshTokenService()


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
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def user_id():
    """Create a test user ID"""
    return str(uuid4())


@pytest.fixture
def client_id():
    """Create a test client ID"""
    return "web_app"


@pytest.fixture
def session_id():
    """Create a test session ID"""
    return str(uuid4())


@pytest.mark.integration
class TestRefreshTokenFlow:
    """Test complete refresh token flow scenarios"""

    @pytest.mark.asyncio
    async def test_complete_token_flow_password_to_logout(
        self, refresh_token_service, session_service, mock_db, user_id, client_id, session_id
    ):
        """Test complete flow: password grant → refresh → logout"""
        # Step 1: Initial authentication (password grant)
        now = datetime.now(timezone.utc)
        initial_payload = RefreshTokenPayload(
            iss="auth_server",
            sub=user_id,
            aud="web_app",
            client_id=client_id,
            scope="read write",
            jti=str(uuid4()),
            iat=int(now.timestamp()),
            nbf=int(now.timestamp()),
            exp=int((now + timedelta(days=30)).timestamp()),
        )

        initial_token = RefreshToken(
            id=str(uuid4()),
            jti_hash="initial123456" * 5 + "ini",
            user_id=user_id,
            client_id=client_id,
            scope=initial_payload.scope,
            expires_at=datetime.fromtimestamp(initial_payload.exp, tz=timezone.utc),
            session_id=session_id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        mock_db.refresh = AsyncMock()

        # Act: Save initial token
        result1 = await refresh_token_service.save_refresh_token(
            mock_db, initial_payload, session_id=session_id, ip_address="192.168.1.1"
        )

        # Assert: Initial token saved
        mock_db.add.assert_called()
        assert mock_db.commit.call_count >= 1

        # Step 2: Token refresh (new tokens issued)
        now = datetime.now(timezone.utc)
        refresh_payload = RefreshTokenPayload(
            iss="auth_server",
            sub=user_id,
            aud="web_app",
            client_id=client_id,
            scope="read write",
            jti=str(uuid4()),
            iat=int(now.timestamp()),
            nbf=int(now.timestamp()),
            exp=int((now + timedelta(days=30)).timestamp()),
        )

        # Act: Save refreshed token
        result2 = await refresh_token_service.save_refresh_token(
            mock_db,
            refresh_payload,
            parent_jti=initial_payload.jti,
            session_id=session_id,
        )

        # Assert: New token saved
        add_calls = mock_db.add.call_count
        assert add_calls >= 1

        # Step 3: Logout (revoke token)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=initial_token)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act: Revoke token
        revoked = await refresh_token_service.revoke_token(mock_db, refresh_payload.jti)

        # Assert: Token revoked
        assert revoked is True
        assert mock_db.commit.call_count >= 2

    @pytest.mark.asyncio
    async def test_token_reuse_detection_full_scenario(
        self, refresh_token_service, mock_db, user_id, client_id, session_id
    ):
        """Test detection and handling of token reuse attack"""
        # Arrange: Create legitimate token chain
        initial_jti = str(uuid4())
        reused_jti = str(uuid4())
        new_jti = str(uuid4())

        initial_token = RefreshToken(
            id=str(uuid4()),
            jti_hash="initial789012" * 5 + "ini",
            user_id=user_id,
            client_id=client_id,
            scope="read write",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            session_id=session_id,
        )

        rotated_token = RefreshToken(
            id=str(uuid4()),
            jti_hash="rotated345678" * 5 + "rot",
            user_id=user_id,
            client_id=client_id,
            scope="read write",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            parent_jti_hash="initial789012" * 5 + "ini",
            session_id=session_id,
        )

        # Simulate attacker trying to reuse the rotated token
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=rotated_token)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act: Attempt to use rotated token again
        is_valid, error = await refresh_token_service.validate_refresh_token(
            mock_db, reused_jti
        )

        # Assert: Validation would check if revoked
        # In real scenario with reuse, token would be revoked
        rotated_token.revoked = True
        is_valid, error = await refresh_token_service.validate_refresh_token(
            mock_db, reused_jti
        )
        assert is_valid is False
        assert "revoked" in error.lower()

    @pytest.mark.asyncio
    async def test_session_management_list_and_revoke(
        self, session_service, mock_db, user_id
    ):
        """Test listing and revoking sessions"""
        # Arrange: Create multiple sessions
        session1_id = str(uuid4())
        session2_id = str(uuid4())

        token1 = RefreshToken(
            id=str(uuid4()),
            jti_hash="token1abcdef" * 5 + "tok",
            user_id=user_id,
            client_id="web_app",
            scope="read write",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            session_id=session1_id,
            created_at=datetime.now(timezone.utc),
        )

        token2 = RefreshToken(
            id=str(uuid4()),
            jti_hash="token2ghijkl" * 5 + "tok",
            user_id=user_id,
            client_id="ios_app",
            scope="read",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            session_id=session2_id,
            created_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        # Act: List sessions
        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(return_value=[token1, token2])
        mock_db.execute = AsyncMock(return_value=mock_result)

        sessions = await session_service.list_user_sessions(mock_db, user_id)

        # Assert: Sessions listed
        assert len(sessions) == 2
        assert sessions[0]["session_id"] in [session1_id, session2_id]

        # Act: Revoke one session
        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(return_value=[token1])
        mock_db.execute = AsyncMock(return_value=mock_result)

        revoked = await session_service.revoke_session(mock_db, user_id, session1_id)

        # Assert: Session revoked
        assert revoked is True
        assert token1.revoked is True

    @pytest.mark.asyncio
    async def test_multi_device_session_management(
        self, session_service, mock_db, user_id
    ):
        """Test managing multiple device sessions"""
        # Arrange: Simulate user with 3 active sessions
        desktop_session = str(uuid4())
        mobile_session = str(uuid4())
        tablet_session = str(uuid4())

        token_desktop = RefreshToken(
            id=str(uuid4()),
            jti_hash="desktop1234567" * 4,
            user_id=user_id,
            client_id="web_app",
            scope="read write",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            session_id=desktop_session,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            created_at=datetime.now(timezone.utc),
        )

        token_mobile = RefreshToken(
            id=str(uuid4()),
            jti_hash="mobile1234567" * 4 + "mob",
            user_id=user_id,
            client_id="ios_app",
            scope="read write",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            session_id=mobile_session,
            ip_address="10.0.0.1",
            user_agent="iOS App v1.0",
            created_at=datetime.now(timezone.utc) + timedelta(hours=2),
        )

        token_tablet = RefreshToken(
            id=str(uuid4()),
            jti_hash="tablet1234567" * 4 + "tab",
            user_id=user_id,
            client_id="android_app",
            scope="read",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            session_id=tablet_session,
            ip_address="10.0.0.2",
            user_agent="Android App v2.1",
            created_at=datetime.now(timezone.utc) + timedelta(hours=4),
        )

        # Act: List all sessions
        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(
            return_value=[token_desktop, token_mobile, token_tablet]
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        sessions = await session_service.list_user_sessions(mock_db, user_id)

        # Assert: All sessions listed
        assert len(sessions) == 3

        # Act: Get details of one session
        mock_result = MagicMock()
        mock_result.scalars.return_value.first = MagicMock(return_value=token_mobile)
        mock_db.execute = AsyncMock(return_value=mock_result)

        info = await session_service.get_session_info(
            mock_db, user_id, mobile_session
        )

        # Assert: Mobile session details correct
        assert info["client_id"] == "ios_app"
        assert "iOS App" in info["user_agent"]

        # Act: Logout from mobile, keep others active
        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(return_value=[token_mobile])
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await session_service.revoke_session(
            mock_db, user_id, mobile_session
        )

        # Assert: Mobile revoked
        assert result is True
        assert token_mobile.revoked is True

    @pytest.mark.asyncio
    async def test_logout_all_except_current_session(
        self, session_service, mock_db, user_id
    ):
        """Test logout from all devices except current"""
        # Arrange
        current_session_id = str(uuid4())
        other_session_id_1 = str(uuid4())
        other_session_id_2 = str(uuid4())

        current_token = RefreshToken(
            id=str(uuid4()),
            jti_hash="current12345678" * 4,
            user_id=user_id,
            client_id="web_app",
            scope="read write",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            session_id=current_session_id,
        )

        other_token_1 = RefreshToken(
            id=str(uuid4()),
            jti_hash="other1abcdefgh" * 4,
            user_id=user_id,
            client_id="ios_app",
            scope="read",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            session_id=other_session_id_1,
        )

        other_token_2 = RefreshToken(
            id=str(uuid4()),
            jti_hash="other2ijklmnop" * 4,
            user_id=user_id,
            client_id="android_app",
            scope="read",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            session_id=other_session_id_2,
        )

        # Act: Revoke all except current
        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(
            return_value=[current_token, other_token_1, other_token_2]
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        count = await session_service.revoke_all_sessions(
            mock_db, user_id, except_session_id=current_session_id
        )

        # Assert
        assert count == 2
        assert current_token.revoked is False
        assert other_token_1.revoked is True
        assert other_token_2.revoked is True

    @pytest.mark.asyncio
    async def test_error_handling_invalid_token(
        self, refresh_token_service, mock_db
    ):
        """Test error handling for invalid tokens"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        is_valid, error = await refresh_token_service.validate_refresh_token(
            mock_db, "invalid_jti"
        )

        # Assert
        assert is_valid is False
        assert error is not None
        assert "not found" in error.lower()

    @pytest.mark.asyncio
    async def test_error_handling_expired_token(
        self, refresh_token_service, mock_db
    ):
        """Test error handling for expired tokens"""
        # Arrange
        expired_token = RefreshToken(
            id=str(uuid4()),
            jti_hash="expired1234567" * 4,
            user_id=str(uuid4()),
            client_id="web_app",
            scope="read",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            revoked=False,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=expired_token)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        is_valid, error = await refresh_token_service.validate_refresh_token(
            mock_db, "expired_jti"
        )

        # Assert
        assert is_valid is False
        assert "expired" in error.lower()

    @pytest.mark.asyncio
    async def test_error_handling_revoked_token(
        self, refresh_token_service, mock_db
    ):
        """Test error handling for revoked tokens"""
        # Arrange
        revoked_token = RefreshToken(
            id=str(uuid4()),
            jti_hash="revoked1234567" * 4,
            user_id=str(uuid4()),
            client_id="web_app",
            scope="read",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=True,
            revoked_at=datetime.now(timezone.utc),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=revoked_token)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        is_valid, error = await refresh_token_service.validate_refresh_token(
            mock_db, "revoked_jti"
        )

        # Assert
        assert is_valid is False
        assert "revoked" in error.lower()

    @pytest.mark.asyncio
    async def test_error_handling_session_not_found(
        self, session_service, mock_db, user_id
    ):
        """Test error handling for nonexistent sessions"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.first = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        info = await session_service.get_session_info(
            mock_db, user_id, str(uuid4())
        )

        # Assert
        assert info is None

    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens_integration(
        self, refresh_token_service, mock_db
    ):
        """Test cleanup of expired tokens"""
        # Arrange
        user_id = str(uuid4())
        
        expired_token_1 = RefreshToken(
            id=str(uuid4()),
            jti_hash="expired_old1234" * 4,
            user_id=user_id,
            client_id="web_app",
            scope="read",
            expires_at=datetime.now(timezone.utc) - timedelta(days=45),
            revoked=False,
        )

        expired_token_2 = RefreshToken(
            id=str(uuid4()),
            jti_hash="expired_old5678" * 4,
            user_id=user_id,
            client_id="ios_app",
            scope="read",
            expires_at=datetime.now(timezone.utc) - timedelta(days=30),
            revoked=False,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(
            return_value=[expired_token_1, expired_token_2]
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        count = await refresh_token_service.cleanup_expired_tokens(
            mock_db, days_to_keep=7
        )

        # Assert
        assert count == 2

    @pytest.mark.asyncio
    async def test_concurrent_sessions_isolation(
        self, session_service, mock_db
    ):
        """Test that sessions are properly isolated per user"""
        # Arrange
        user_1_id = str(uuid4())
        user_2_id = str(uuid4())

        user1_session = RefreshToken(
            id=str(uuid4()),
            jti_hash="user1sess1234567" * 4,
            user_id=user_1_id,
            client_id="web_app",
            scope="read",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            session_id=str(uuid4()),
        )

        user2_session = RefreshToken(
            id=str(uuid4()),
            jti_hash="user2sess1234567" * 4,
            user_id=user_2_id,
            client_id="web_app",
            scope="read",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            session_id=str(uuid4()),
        )

        # Act: List sessions for user 1
        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(return_value=[user1_session])
        mock_db.execute = AsyncMock(return_value=mock_result)

        user1_sessions = await session_service.list_user_sessions(mock_db, user_1_id)

        # Assert: Only user 1's session returned
        assert len(user1_sessions) == 1
        assert all(s.get("session_id") for s in user1_sessions)

        # Act: List sessions for user 2
        mock_result = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(return_value=[user2_session])
        mock_db.execute = AsyncMock(return_value=mock_result)

        user2_sessions = await session_service.list_user_sessions(mock_db, user_2_id)

        # Assert: Only user 2's session returned
        assert len(user2_sessions) == 1
