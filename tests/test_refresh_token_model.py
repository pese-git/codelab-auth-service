"""Tests for RefreshToken model"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.models.refresh_token import RefreshToken


class TestRefreshTokenModel:
    """Test RefreshToken model properties and methods"""

    @pytest.fixture
    def valid_token(self):
        """Create a valid refresh token instance"""
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

    @pytest.fixture
    def expired_token(self):
        """Create an expired refresh token"""
        return RefreshToken(
            id=str(uuid4()),
            jti_hash="xyz789uvw012" * 5 + "xyz",  # 64 chars
            user_id=str(uuid4()),
            client_id="web_app",
            scope="read write",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
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

    @pytest.fixture
    def revoked_token(self):
        """Create a revoked refresh token"""
        return RefreshToken(
            id=str(uuid4()),
            jti_hash="def456ghi789" * 5 + "def",  # 64 chars
            user_id=str(uuid4()),
            client_id="web_app",
            scope="read write",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=True,
            revoked_at=datetime.now(timezone.utc),
            parent_jti_hash=None,
            session_id=str(uuid4()),
            last_used=datetime.now(timezone.utc),
            last_rotated_at=datetime.now(timezone.utc),
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            created_at=datetime.now(timezone.utc),
        )

    def test_is_expired_with_valid_token(self, valid_token):
        """Test is_expired property returns False for valid token"""
        assert valid_token.is_expired is False

    def test_is_expired_with_expired_token(self, expired_token):
        """Test is_expired property returns True for expired token"""
        assert expired_token.is_expired is True

    def test_is_valid_with_valid_token(self, valid_token):
        """Test is_valid property returns True for valid token"""
        assert valid_token.is_valid is True

    def test_is_valid_with_revoked_token(self, revoked_token):
        """Test is_valid property returns False for revoked token"""
        assert revoked_token.is_valid is False

    def test_is_valid_with_expired_token(self, expired_token):
        """Test is_valid property returns False for expired token"""
        assert expired_token.is_valid is False

    def test_is_current_with_valid_token_with_last_used(self, valid_token):
        """Test is_current property returns True for valid token with last_used"""
        assert valid_token.is_current is True

    def test_is_current_with_token_without_last_used(self, valid_token):
        """Test is_current property returns False when last_used is None"""
        valid_token.last_used = None
        assert valid_token.is_current is False

    def test_is_current_with_revoked_token(self, revoked_token):
        """Test is_current property returns False for revoked token"""
        assert revoked_token.is_current is False

    def test_is_current_with_expired_token(self, expired_token):
        """Test is_current property returns False for expired token"""
        assert expired_token.is_current is False

    def test_repr(self, valid_token):
        """Test token representation"""
        repr_str = repr(valid_token)
        assert "<RefreshToken(" in repr_str
        assert f"id={valid_token.id}" in repr_str
        assert f"user_id={valid_token.user_id}" in repr_str
        assert f"revoked={valid_token.revoked}" in repr_str

    def test_token_with_parent_jti(self):
        """Test token with parent_jti_hash for rotation chain"""
        parent_hash = "parent123456789" * 4 + "par"  # 64 chars
        token = RefreshToken(
            id=str(uuid4()),
            jti_hash="child123456789" * 4 + "chi",
            user_id=str(uuid4()),
            client_id="web_app",
            scope="read write",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked=False,
            revoked_at=None,
            parent_jti_hash=parent_hash,
            session_id=str(uuid4()),
            last_used=datetime.now(timezone.utc),
            last_rotated_at=datetime.now(timezone.utc),
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            created_at=datetime.now(timezone.utc),
        )

        assert token.parent_jti_hash == parent_hash
        assert token.is_valid is True

    def test_token_with_session_id(self, valid_token):
        """Test token session_id tracking"""
        session_id = str(uuid4())
        valid_token.session_id = session_id
        assert valid_token.session_id == session_id

    def test_token_with_metadata(self, valid_token):
        """Test token metadata fields (ip_address, user_agent)"""
        assert valid_token.ip_address == "192.168.1.1"
        assert valid_token.user_agent == "Mozilla/5.0"

    def test_token_with_ipv6_address(self):
        """Test token with IPv6 address"""
        token = RefreshToken(
            id=str(uuid4()),
            jti_hash="ipv6123456789" * 4 + "ipv",
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
            ip_address="2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            user_agent="Mozilla/5.0",
            created_at=datetime.now(timezone.utc),
        )

        assert token.ip_address == "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        assert token.is_valid is True

    def test_token_scope_field(self, valid_token):
        """Test token scope field"""
        assert valid_token.scope == "read write"
        assert "read" in valid_token.scope

    def test_token_rotation_timestamps(self, valid_token):
        """Test token rotation timestamps"""
        assert valid_token.last_rotated_at is not None
        assert valid_token.last_used is not None
        assert valid_token.created_at is not None

    def test_token_created_with_defaults(self):
        """Test token creation with default values"""
        token = RefreshToken(
            id=str(uuid4()),
            jti_hash="defaults123456" * 4 + "def",
            user_id=str(uuid4()),
            client_id="web_app",
            scope="read",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            session_id=str(uuid4()),
        )

        assert token.revoked is False
        assert token.revoked_at is None
        assert token.parent_jti_hash is None
        assert token.last_used is None
        assert token.last_rotated_at is None
        assert token.ip_address is None
        assert token.user_agent is None
        assert token.created_at is not None
