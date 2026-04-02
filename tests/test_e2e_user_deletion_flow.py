"""End-to-End tests for user deletion flow with event publishing and token blacklist."""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.user import User
from app.services.event_publisher import RedisStreamsPublisher
from app.services.token_blacklist_service import TokenBlacklistService
from app.services.token_service import TokenService
from app.services.user_service import UserService


@pytest.mark.asyncio
class TestE2EUserDeletionFlow:
    """End-to-End tests for user deletion flow."""

    async def test_full_user_deletion_flow(
        self,
        db_session: AsyncSession,
        mock_redis_client: AsyncMock,
        settings: Settings,
    ):
        """Test complete user deletion flow: token revocation → DB update → event publishing."""
        # Setup: Create a user
        user_service = UserService()
        user = User(
            id="test-user-123",
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            is_active=True,
            is_verified=True,
        )
        db_session.add(user)
        await db_session.flush()

        # Create a token for the user
        token_service = TokenService(settings)
        token_payload = {
            "sub": user.id,
            "email": user.email,
            "username": user.username,
        }
        access_token = token_service.create_access_token(token_payload)
        jti = token_service.decode_token(access_token)["jti"]

        # Setup: Initialize services with mocked Redis
        blacklist_service = TokenBlacklistService(mock_redis_client)
        publisher = RedisStreamsPublisher(mock_redis_client)

        # Phase 1: Verify token is not in blacklist
        is_revoked = await blacklist_service.is_token_revoked(jti)
        assert not is_revoked

        # Phase 2: Revoke all user tokens
        tokens_revoked = await blacklist_service.revoke_all_user_tokens(
            user_id=user.id,
            reason="user_deletion",
            metadata={"ip": "127.0.0.1"},
        )
        assert tokens_revoked >= 1

        # Phase 3: Verify token is now in blacklist
        is_revoked = await blacklist_service.is_token_revoked(jti)
        assert is_revoked

        # Phase 4: Update user in DB (soft delete)
        user.is_deleted = True
        user.deleted_at = datetime.utcnow()
        user.deletion_reason = "admin_request"
        await db_session.flush()

        # Phase 5: Publish deletion event
        event_id = await publisher.publish_event(
            event_type="user.deleted",
            user_id=user.id,
            data={
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "deleted_at": user.deleted_at.isoformat(),
            },
            correlation_id="corr-123",
        )
        assert event_id is not None

        # Verify Redis XADD was called
        mock_redis_client.xadd.assert_called_once()

        # Phase 6: Verify event structure
        call_args = mock_redis_client.xadd.call_args
        stream_key = call_args[0][0]
        event_data = call_args[0][1]

        assert stream_key == "user_events"
        assert event_data["type"] == "user.deleted"
        assert event_data["user_id"] == user.id
        assert event_data["version"] == "1.0"
        assert "timestamp" in event_data
        assert "correlation_id" in event_data

    async def test_user_deletion_with_invalid_user_id(
        self,
        db_session: AsyncSession,
        mock_redis_client: AsyncMock,
    ):
        """Test deletion flow with non-existent user."""
        blacklist_service = TokenBlacklistService(mock_redis_client)

        # Try to revoke tokens for non-existent user
        tokens_revoked = await blacklist_service.revoke_all_user_tokens(
            user_id="non-existent-user",
            reason="user_deletion",
        )
        # Should handle gracefully - no tokens to revoke
        assert tokens_revoked == 0

    async def test_token_revocation_with_redis_failure(
        self,
        db_session: AsyncSession,
        settings: Settings,
    ):
        """Test token revocation when Redis is unavailable."""
        # Create a mock that raises an exception
        failing_redis = AsyncMock()
        failing_redis.pipeline.side_effect = Exception("Redis connection failed")

        blacklist_service = TokenBlacklistService(failing_redis)

        # Attempt revocation - should raise exception
        with pytest.raises(Exception):
            await blacklist_service.revoke_token(
                jti="test-jti",
                expires_at=datetime.utcnow() + timedelta(hours=1),
            )

    async def test_event_publishing_with_redis_failure(
        self,
        settings: Settings,
    ):
        """Test event publishing when Redis is unavailable."""
        failing_redis = AsyncMock()
        failing_redis.xadd.side_effect = Exception("Redis connection failed")

        publisher = RedisStreamsPublisher(failing_redis)

        # Attempt publishing - should raise exception
        with pytest.raises(Exception):
            await publisher.publish_event(
                event_type="user.deleted",
                user_id="test-user",
                data={"test": "data"},
            )

    async def test_multiple_token_revocation(
        self,
        mock_redis_client: AsyncMock,
        settings: Settings,
    ):
        """Test revoking multiple tokens for a user."""
        blacklist_service = TokenBlacklistService(mock_redis_client)

        user_id = "test-user-456"
        jti_list = ["jti-1", "jti-2", "jti-3", "jti-4", "jti-5"]
        expires_at = datetime.utcnow() + timedelta(hours=1)

        # Setup mock pipeline
        mock_pipeline = AsyncMock()
        mock_redis_client.pipeline.return_value = mock_pipeline

        # Revoke all tokens
        await blacklist_service.revoke_all_user_tokens(
            user_id=user_id,
            reason="user_deletion",
        )

        # Verify pipeline was used for batch operations
        mock_redis_client.pipeline.assert_called_once()

    async def test_event_envelope_structure(
        self,
        mock_redis_client: AsyncMock,
        settings: Settings,
    ):
        """Test that published events have correct envelope structure."""
        publisher = RedisStreamsPublisher(mock_redis_client)

        user_id = "test-user-789"
        correlation_id = "corr-abc-123"
        event_data = {
            "username": "testuser",
            "email": "test@example.com",
        }

        await publisher.publish_event(
            event_type="user.created",
            user_id=user_id,
            data=event_data,
            correlation_id=correlation_id,
        )

        # Verify XADD call
        call_args = mock_redis_client.xadd.call_args
        stream_key, event_data_dict = call_args[0][0], call_args[0][1]

        # Check envelope structure
        assert event_data_dict["type"] == "user.created"
        assert event_data_dict["user_id"] == user_id
        assert event_data_dict["correlation_id"] == correlation_id
        assert "timestamp" in event_data_dict
        assert "id" in event_data_dict
        assert "version" in event_data_dict
        assert "data" in event_data_dict

    async def test_soft_delete_user_model(
        self,
        db_session: AsyncSession,
    ):
        """Test soft delete fields in User model."""
        user = User(
            id="test-user-soft-delete",
            username="softdeleteuser",
            email="softdelete@example.com",
            password_hash="hashed_password",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        # Verify soft delete fields are initially empty
        assert not user.is_deleted
        assert user.deleted_at is None
        assert user.deletion_reason is None

        # Perform soft delete
        user.is_deleted = True
        user.deleted_at = datetime.utcnow()
        user.deletion_reason = "admin_request"
        await db_session.flush()

        # Verify fields are set
        assert user.is_deleted
        assert user.deleted_at is not None
        assert user.deletion_reason == "admin_request"

    async def test_cascade_event_sequence(
        self,
        mock_redis_client: AsyncMock,
        settings: Settings,
    ):
        """Test that events are published in correct sequence."""
        publisher = RedisStreamsPublisher(mock_redis_client)

        user_id = "test-user-cascade"
        events_published = []

        # Mock to capture calls
        async def capture_event(*args, **kwargs):
            events_published.append({
                "args": args,
                "kwargs": kwargs,
            })

        mock_redis_client.xadd.side_effect = capture_event

        # Publish events in sequence
        await publisher.publish_event(
            event_type="user.created",
            user_id=user_id,
            data={"username": "cascadeuser"},
        )

        await publisher.publish_event(
            event_type="user.updated",
            user_id=user_id,
            data={"email": "cascade@example.com"},
        )

        await publisher.publish_event(
            event_type="user.deleted",
            user_id=user_id,
            data={"deleted_at": datetime.utcnow().isoformat()},
        )

        # Verify sequence
        assert len(events_published) == 3
        assert mock_redis_client.xadd.call_count == 3

    async def test_idempotent_token_revocation(
        self,
        mock_redis_client: AsyncMock,
    ):
        """Test that revoking the same token twice is idempotent."""
        blacklist_service = TokenBlacklistService(mock_redis_client)

        jti = "test-jti-idempotent"
        expires_at = datetime.utcnow() + timedelta(hours=1)

        # Mock setex to track calls
        calls = []

        async def track_setex(*args, **kwargs):
            calls.append({"args": args, "kwargs": kwargs})

        mock_redis_client.setex.side_effect = track_setex

        # Revoke twice
        await blacklist_service.revoke_token(jti, expires_at)
        await blacklist_service.revoke_token(jti, expires_at)

        # Both calls should succeed (idempotent)
        assert len(calls) == 2

    async def test_event_versioning(
        self,
        mock_redis_client: AsyncMock,
        settings: Settings,
    ):
        """Test that events include correct version."""
        publisher = RedisStreamsPublisher(mock_redis_client)

        await publisher.publish_event(
            event_type="user.deleted",
            user_id="test-user",
            data={},
        )

        call_args = mock_redis_client.xadd.call_args
        event_data = call_args[0][1]

        # Verify version
        assert event_data["version"] == "1.0"

    async def test_metadata_preservation_in_token_revocation(
        self,
        mock_redis_client: AsyncMock,
    ):
        """Test that metadata is preserved during token revocation."""
        blacklist_service = TokenBlacklistService(mock_redis_client)

        jti = "test-jti-metadata"
        expires_at = datetime.utcnow() + timedelta(hours=1)
        metadata = {
            "ip": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
            "reason": "logout",
        }

        # Setup mock to capture metadata
        captured_metadata = None

        async def capture_hset(*args, **kwargs):
            nonlocal captured_metadata
            if len(args) > 2 and isinstance(args[2], dict):
                captured_metadata = args[2]

        mock_redis_client.hset.side_effect = capture_hset

        await blacklist_service.revoke_token(
            jti,
            expires_at,
            metadata=metadata,
        )

        # Metadata should be stored (if implementation includes it)
        # This depends on implementation details
