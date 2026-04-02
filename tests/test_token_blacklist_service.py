"""Unit tests for TokenBlacklistService"""

import asyncio
import time
from uuid import uuid4

import pytest
import pytest_asyncio
from redis import Redis

from app.services.token_blacklist_service import TokenBlacklistService


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
async def blacklist_service(redis_client):
    """Create TokenBlacklistService instance for testing"""
    return TokenBlacklistService(redis_client)


@pytest.mark.asyncio
async def test_revoke_token_success(blacklist_service):
    """Test successful token revocation"""
    user_id = str(uuid4())
    jti = str(uuid4())
    exp = int(time.time()) + 3600
    
    result = await blacklist_service.revoke_token(
        token_jti=jti,
        user_id=user_id,
        exp_timestamp=exp,
        reason="user_logout"
    )
    
    assert result is True
    
    # Verify token is in blacklist
    is_revoked = await blacklist_service.is_token_revoked(jti)
    assert is_revoked is True


@pytest.mark.asyncio
async def test_revoke_token_already_expired(blacklist_service):
    """Test revoking already expired token returns False"""
    user_id = str(uuid4())
    jti = str(uuid4())
    exp = int(time.time()) - 3600  # In the past
    
    result = await blacklist_service.revoke_token(
        token_jti=jti,
        user_id=user_id,
        exp_timestamp=exp,
        reason="user_logout"
    )
    
    assert result is False
    
    # Verify token is NOT in blacklist
    is_revoked = await blacklist_service.is_token_revoked(jti)
    assert is_revoked is False


@pytest.mark.asyncio
async def test_is_token_revoked_success(blacklist_service):
    """Test checking if token is revoked"""
    user_id = str(uuid4())
    jti = str(uuid4())
    exp = int(time.time()) + 3600
    
    # Revoke token
    await blacklist_service.revoke_token(
        token_jti=jti,
        user_id=user_id,
        exp_timestamp=exp,
    )
    
    # Check revocation
    is_revoked = await blacklist_service.is_token_revoked(jti)
    assert is_revoked is True


@pytest.mark.asyncio
async def test_is_token_revoked_not_exists(blacklist_service):
    """Test checking non-existent token returns False"""
    jti = str(uuid4())
    
    is_revoked = await blacklist_service.is_token_revoked(jti)
    assert is_revoked is False


@pytest.mark.asyncio
async def test_revoke_all_user_tokens_success(blacklist_service):
    """Test batch revocation of all user tokens"""
    user_id = str(uuid4())
    now = int(time.time())
    
    token_list = [
        (str(uuid4()), now + 3600),
        (str(uuid4()), now + 7200),
        (str(uuid4()), now + 10800),
    ]
    
    revoked_count = await blacklist_service.revoke_all_user_tokens(
        user_id=user_id,
        token_list=token_list
    )
    
    assert revoked_count == 3
    
    # Verify all tokens are revoked
    for jti, _ in token_list:
        is_revoked = await blacklist_service.is_token_revoked(jti)
        assert is_revoked is True


@pytest.mark.asyncio
async def test_revoke_all_user_tokens_empty_list(blacklist_service):
    """Test batch revocation with empty token list"""
    user_id = str(uuid4())
    
    revoked_count = await blacklist_service.revoke_all_user_tokens(
        user_id=user_id,
        token_list=[]
    )
    
    assert revoked_count == 0


@pytest.mark.asyncio
async def test_revoke_all_user_tokens_mixed_expiry(blacklist_service):
    """Test batch revocation with mixed expired/valid tokens"""
    user_id = str(uuid4())
    now = int(time.time())
    
    token_list = [
        (str(uuid4()), now + 3600),  # Valid
        (str(uuid4()), now - 3600),  # Already expired
        (str(uuid4()), now + 7200),  # Valid
    ]
    
    revoked_count = await blacklist_service.revoke_all_user_tokens(
        user_id=user_id,
        token_list=token_list
    )
    
    # Should only revoke 2 (non-expired)
    assert revoked_count == 2


@pytest.mark.asyncio
async def test_get_token_metadata(blacklist_service):
    """Test retrieving token metadata"""
    user_id = str(uuid4())
    jti = str(uuid4())
    exp = int(time.time()) + 3600
    admin_id = str(uuid4())
    
    # Revoke with admin
    await blacklist_service.revoke_token(
        token_jti=jti,
        user_id=user_id,
        exp_timestamp=exp,
        reason="admin_revoke",
        admin_id=admin_id,
    )
    
    # Get metadata
    metadata = await blacklist_service.get_token_metadata(jti)
    
    assert metadata is not None
    assert metadata["user_id"] == user_id
    assert metadata["reason"] == "admin_revoke"
    assert metadata["admin_id"] == admin_id
    assert "revoked_at" in metadata


@pytest.mark.asyncio
async def test_get_token_metadata_not_exists(blacklist_service):
    """Test getting metadata for non-existent token"""
    jti = str(uuid4())
    
    metadata = await blacklist_service.get_token_metadata(jti)
    
    assert metadata is None


@pytest.mark.asyncio
async def test_token_ttl_expiration(blacklist_service):
    """Test that tokens expire from Redis after TTL"""
    user_id = str(uuid4())
    jti = str(uuid4())
    exp = int(time.time()) + 2  # Expires in 2 seconds
    
    # Revoke token
    await blacklist_service.revoke_token(
        token_jti=jti,
        user_id=user_id,
        exp_timestamp=exp,
    )
    
    # Verify revoked now
    assert await blacklist_service.is_token_revoked(jti) is True
    
    # Wait for TTL to expire
    await asyncio.sleep(3)
    
    # Verify cleaned up
    is_revoked = await blacklist_service.is_token_revoked(jti)
    assert is_revoked is False


@pytest.mark.asyncio
async def test_cleanup_user_tokens(blacklist_service):
    """Test cleanup of expired user tokens"""
    user_id = str(uuid4())
    now = int(time.time())
    
    # Create tokens with different expiry times
    token_list = [
        (str(uuid4()), now + 3600),  # 1 hour
        (str(uuid4()), now + 1),     # 1 second (will expire)
    ]
    
    # Revoke all
    await blacklist_service.revoke_all_user_tokens(
        user_id=user_id,
        token_list=token_list
    )
    
    # Wait for second token to expire
    await asyncio.sleep(2)
    
    # Cleanup
    cleaned_count = await blacklist_service.cleanup_user_tokens(user_id)
    
    # Should have cleaned up 1 token
    assert cleaned_count == 1
    
    # Remaining token should still be revoked
    first_jti = token_list[0][0]
    assert await blacklist_service.is_token_revoked(first_jti) is True


@pytest.mark.asyncio
async def test_idempotent_revocation(blacklist_service):
    """Test that revoking same token multiple times is idempotent"""
    user_id = str(uuid4())
    jti = str(uuid4())
    exp = int(time.time()) + 3600
    
    # Revoke twice
    result1 = await blacklist_service.revoke_token(
        token_jti=jti,
        user_id=user_id,
        exp_timestamp=exp,
    )
    
    result2 = await blacklist_service.revoke_token(
        token_jti=jti,
        user_id=user_id,
        exp_timestamp=exp,
    )
    
    assert result1 is True
    assert result2 is True
    
    # Token should still be revoked
    is_revoked = await blacklist_service.is_token_revoked(jti)
    assert is_revoked is True
