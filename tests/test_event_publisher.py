"""Unit tests for EventPublisher"""

import json
import asyncio
from uuid import uuid4

import pytest
import pytest_asyncio
from redis import Redis

from app.services.event_publisher import RedisStreamsPublisher


@pytest_asyncio.fixture
async def redis_client():
    """Create Redis client for testing"""
    client = Redis(host='localhost', port=6379, db=1)
    # Clean up before test
    await client.flushdb()
    yield client
    # Clean up after test
    await client.flushdb()


@pytest_asyncio.fixture
async def publisher(redis_client):
    """Create RedisStreamsPublisher instance for testing"""
    pub = RedisStreamsPublisher(redis_client)
    await pub.initialize()
    return pub


@pytest.mark.asyncio
async def test_initialize_success(redis_client):
    """Test successful publisher initialization"""
    publisher = RedisStreamsPublisher(redis_client)
    await publisher.initialize()
    # Should not raise any exception


@pytest.mark.asyncio
async def test_publish_event_success(publisher):
    """Test successful event publication"""
    user_id = str(uuid4())
    
    message_id = await publisher.publish_event(
        event_type="user.created",
        aggregate_type="user",
        aggregate_id=user_id,
        data={
            "user_id": user_id,
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe",
        }
    )
    
    assert message_id is not None
    assert isinstance(message_id, str)
    assert "-" in message_id  # Redis stream ID format


@pytest.mark.asyncio
async def test_publish_event_returns_valid_id(publisher):
    """Test that published event has valid Redis stream ID"""
    message_id = await publisher.publish_event(
        event_type="user.deleted",
        aggregate_type="user",
        aggregate_id=str(uuid4()),
        data={"user_id": str(uuid4())}
    )
    
    # Redis stream ID format: timestamp-sequence
    parts = message_id.split("-")
    assert len(parts) == 2
    assert parts[0].isdigit()
    assert parts[1].isdigit()


@pytest.mark.asyncio
async def test_publish_event_with_correlation_id(publisher, redis_client):
    """Test correlation ID preservation"""
    user_id = str(uuid4())
    correlation_id = str(uuid4())
    
    await publisher.publish_event(
        event_type="user.created",
        aggregate_type="user",
        aggregate_id=user_id,
        data={"user_id": user_id, "email": "user@example.com"},
        correlation_id=correlation_id
    )
    
    # Read from stream and verify
    events = await redis_client.xread(
        {publisher.STREAM_KEY: "0"},
        count=1
    )
    
    assert events is not None
    message_id, message_data = events[0][1][0]
    
    # Verify correlation_id matches
    stored_correlation_id = message_data[b"correlation_id"].decode()
    assert stored_correlation_id == correlation_id


@pytest.mark.asyncio
async def test_publish_event_creates_envelope(publisher, redis_client):
    """Test that event envelope is properly created"""
    user_id = str(uuid4())
    email = "test@example.com"
    
    await publisher.publish_event(
        event_type="user.created",
        aggregate_type="user",
        aggregate_id=user_id,
        data={
            "user_id": user_id,
            "email": email,
        }
    )
    
    # Read from stream
    events = await redis_client.xread(
        {publisher.STREAM_KEY: "0"},
        count=1
    )
    
    message_id, message_data = events[0][1][0]
    
    # Verify all required fields
    assert b"event_id" in message_data
    assert b"event_type" in message_data
    assert b"event_version" in message_data
    assert b"timestamp" in message_data
    assert b"aggregate_type" in message_data
    assert b"aggregate_id" in message_data
    assert b"correlation_id" in message_data
    assert b"source" in message_data
    assert b"data" in message_data
    
    # Verify values
    assert message_data[b"event_type"].decode() == "user.created"
    assert message_data[b"aggregate_type"].decode() == "user"
    assert message_data[b"source"].decode() == "auth-service"


@pytest.mark.asyncio
async def test_publish_event_empty_type_raises_error(publisher):
    """Test that empty event_type raises ValueError"""
    with pytest.raises(ValueError, match="event_type cannot be empty"):
        await publisher.publish_event(
            event_type="",
            aggregate_type="user",
            aggregate_id=str(uuid4()),
            data={}
        )


@pytest.mark.asyncio
async def test_publish_event_non_dict_data_raises_error(publisher):
    """Test that non-dict data raises TypeError"""
    with pytest.raises(TypeError, match="data must be a dict"):
        await publisher.publish_event(
            event_type="user.created",
            aggregate_type="user",
            aggregate_id=str(uuid4()),
            data="not a dict"  # Invalid
        )


@pytest.mark.asyncio
async def test_publish_user_created(publisher, redis_client):
    """Test convenience method for user.created event"""
    user_id = str(uuid4())
    email = "user@example.com"
    
    message_id = await publisher.publish_user_created(
        user_id=user_id,
        email=email,
        first_name="John",
        last_name="Doe"
    )
    
    assert message_id is not None
    
    # Verify event in stream
    events = await redis_client.xread(
        {publisher.STREAM_KEY: "0"},
        count=1
    )
    
    message_id_from_stream, message_data = events[0][1][0]
    assert message_data[b"event_type"].decode() == "user.created"


@pytest.mark.asyncio
async def test_publish_user_deleted(publisher, redis_client):
    """Test convenience method for user.deleted event"""
    user_id = str(uuid4())
    email = "user@example.com"
    
    message_id = await publisher.publish_user_deleted(
        user_id=user_id,
        email=email,
        reason="admin_deletion"
    )
    
    assert message_id is not None
    
    # Verify event in stream
    events = await redis_client.xread(
        {publisher.STREAM_KEY: "0"},
        count=1
    )
    
    _, message_data = events[0][1][0]
    assert message_data[b"event_type"].decode() == "user.deleted"


@pytest.mark.asyncio
async def test_publish_token_revoked(publisher, redis_client):
    """Test convenience method for token.revoked event"""
    token_jti = str(uuid4())
    user_id = str(uuid4())
    
    message_id = await publisher.publish_token_revoked(
        token_jti=token_jti,
        user_id=user_id,
        reason="user_requested"
    )
    
    assert message_id is not None
    
    # Verify event in stream
    events = await redis_client.xread(
        {publisher.STREAM_KEY: "0"},
        count=1
    )
    
    _, message_data = events[0][1][0]
    assert message_data[b"event_type"].decode() == "token.revoked"


@pytest.mark.asyncio
async def test_publish_multiple_events(publisher, redis_client):
    """Test publishing multiple events sequentially"""
    for i in range(5):
        await publisher.publish_event(
            event_type="user.created",
            aggregate_type="user",
            aggregate_id=str(uuid4()),
            data={"user_id": str(uuid4()), "email": f"user{i}@example.com"}
        )
    
    # Verify all events in stream
    events = await redis_client.xread(
        {publisher.STREAM_KEY: "0"}
    )
    
    assert len(events[0][1]) == 5


@pytest.mark.asyncio
async def test_publish_event_data_serialization(publisher, redis_client):
    """Test that event data is properly JSON serialized"""
    user_id = str(uuid4())
    
    await publisher.publish_event(
        event_type="user.created",
        aggregate_type="user",
        aggregate_id=user_id,
        data={
            "user_id": user_id,
            "email": "test@example.com",
            "nested": {
                "field": "value",
                "number": 42
            }
        }
    )
    
    # Read and verify
    events = await redis_client.xread(
        {publisher.STREAM_KEY: "0"},
        count=1
    )
    
    _, message_data = events[0][1][0]
    data_json = message_data[b"data"].decode()
    data_dict = json.loads(data_json)
    
    assert data_dict["user_id"] == user_id
    assert data_dict["nested"]["number"] == 42


@pytest.mark.asyncio
async def test_maxlen_pruning(publisher, redis_client):
    """Test that MAXLEN pruning works (streams don't grow unbounded)"""
    # Publish more events than MAXLEN
    for i in range(publisher.STREAM_MAXLEN + 1000):
        await publisher.publish_event(
            event_type="user.created",
            aggregate_type="user",
            aggregate_id=str(uuid4()),
            data={"user_id": str(uuid4())}
        )
    
    # Check stream length
    stream_len = await redis_client.xlen(publisher.STREAM_KEY)
    
    # Should be approximately MAXLEN (with some tolerance for async)
    assert stream_len <= publisher.STREAM_MAXLEN + 100


@pytest.mark.asyncio
async def test_causation_id_tracking(publisher, redis_client):
    """Test causation ID for event chain tracking"""
    user_id = str(uuid4())
    causation_id = str(uuid4())
    
    await publisher.publish_event(
        event_type="user.created",
        aggregate_type="user",
        aggregate_id=user_id,
        data={"user_id": user_id},
        causation_id=causation_id
    )
    
    # Read and verify
    events = await redis_client.xread(
        {publisher.STREAM_KEY: "0"},
        count=1
    )
    
    _, message_data = events[0][1][0]
    stored_causation_id = message_data[b"causation_id"].decode()
    assert stored_causation_id == causation_id


@pytest.mark.asyncio
async def test_event_version_field(publisher, redis_client):
    """Test that event_version is set correctly"""
    await publisher.publish_event(
        event_type="user.created",
        aggregate_type="user",
        aggregate_id=str(uuid4()),
        data={}
    )
    
    # Read and verify
    events = await redis_client.xread(
        {publisher.STREAM_KEY: "0"},
        count=1
    )
    
    _, message_data = events[0][1][0]
    event_version = message_data[b"event_version"].decode()
    assert event_version == publisher.EVENT_VERSION
