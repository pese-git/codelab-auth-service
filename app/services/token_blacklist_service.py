"""Token blacklist service for managing revoked JWT tokens"""

import json
import time
from typing import Optional
from uuid import UUID

from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.config import logger
from app.services.monitoring import (
    TokenBlacklistMetrics,
    RedisMetrics,
    audit_logger,
)


class TokenBlacklistService:
    """
    Service for managing token blacklist in Redis.
    
    Handles revocation of JWT tokens and batch revocation of all user tokens.
    Uses Redis for fast lookups with automatic TTL-based cleanup.
    """

    BLACKLIST_PREFIX = "token_blacklist"
    USER_TOKENS_PREFIX = "user_tokens"
    TOKEN_METADATA_PREFIX = "token_metadata"

    def __init__(self, redis: Redis):
        """
        Initialize the token blacklist service.
        
        Args:
            redis: Redis async client (redis.asyncio.Redis or redis.Redis)
        """
        self.redis = redis

    async def revoke_token(
        self,
        token_jti: str,
        user_id: str,
        exp_timestamp: int,
        reason: str = "user_requested",
        admin_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> bool:
        """
        Revoke a single token by adding it to the blacklist.
        
        Args:
            token_jti: JWT ID from token payload (jti claim)
            user_id: User ID (sub claim in token)
            exp_timestamp: Unix timestamp of token expiration (exp claim)
            reason: Reason for revocation:
                - "user_requested" — user requested logout
                - "user_deleted" — user account deleted
                - "admin_revoke" — administrator revoked token
            admin_id: UUID of administrator if admin_revoke
            metadata: Additional metadata (optional)
        
        Returns:
            bool: True if token was successfully revoked, False if already expired
        
        Raises:
            RedisConnectionError: if Redis is unavailable
            ValueError: if exp_timestamp is in the past
        """
        try:
            async with RedisMetrics.measure_redis_operation("revoke_token"):
                now = int(time.time())
                
                # Check if token is already expired
                if exp_timestamp <= now:
                    logger.warning(
                        f"Token already expired: jti={token_jti}, "
                        f"exp={exp_timestamp}, now={now}"
                    )
                    return False
                
                # Calculate TTL (in seconds)
                ttl = exp_timestamp - now
                if ttl < 3600:  # Minimum 1 hour
                    ttl = 3600
                
                # Create blacklist key
                blacklist_key = f"{self.BLACKLIST_PREFIX}:{token_jti}"
                
                # Add to main blacklist with TTL
                await self.redis.setex(blacklist_key, ttl, "1")
                
                # Add to user_tokens set for batch operations
                user_tokens_key = f"{self.USER_TOKENS_PREFIX}:{user_id}"
                await self.redis.sadd(user_tokens_key, token_jti)
                
                # Set TTL on user_tokens set (use maximum possible)
                await self.redis.expire(user_tokens_key, ttl)
                
                # Store metadata if requested
                metadata_key = f"{self.TOKEN_METADATA_PREFIX}:{token_jti}"
                metadata_dict = {
                    "user_id": str(user_id),
                    "reason": reason,
                    "revoked_at": now,
                    "admin_id": str(admin_id) if admin_id else None,
                }
                if metadata:
                    metadata_dict.update(metadata)
                
                await self.redis.setex(
                    metadata_key,
                    ttl,
                    json.dumps(metadata_dict, default=str)
                )
                
                logger.info(
                    f"Token revoked: jti={token_jti}, user_id={user_id}, "
                    f"reason={reason}, ttl={ttl}s"
                )
                
                # Record metrics and audit log
                TokenBlacklistMetrics.record_revocation(reason, success=True)
                audit_logger.log_token_revocation(
                    user_id=str(user_id),
                    jti=token_jti,
                    reason=reason,
                    initiator=str(admin_id) if admin_id else None,
                    metadata=metadata,
                )
                
                return True

        except RedisConnectionError as e:
            logger.error(f"Redis connection error during token revocation: {e}")
            RedisMetrics.record_connection_error("revoke_token")
            TokenBlacklistMetrics.record_revocation(reason, success=False)
            raise
        except Exception as e:
            logger.error(f"Unexpected error during token revocation: {e}")
            TokenBlacklistMetrics.record_revocation(reason, success=False)
            raise

    async def revoke_all_user_tokens(
        self,
        user_id: str,
        token_list: list[tuple[str, int]],
        reason: str = "user_deleted",
        admin_id: Optional[str] = None,
    ) -> int:
        """
        Revoke all active tokens of a user in a single batch operation.
        
        Args:
            user_id: User ID
            token_list: List of tuples (jti, exp_timestamp)
            reason: Reason for revocation
            admin_id: UUID of administrator if admin_revoke
        
        Returns:
            int: Number of tokens successfully revoked
        
        Raises:
            RedisConnectionError: if Redis is unavailable
        """
        try:
            async with RedisMetrics.measure_redis_operation("revoke_all_user_tokens"):
                if not token_list:
                    logger.info(f"No tokens to revoke for user: {user_id}")
                    return 0
                
                now = int(time.time())
                revoked_count = 0
                
                # Use pipeline for atomic batch operation
                pipe = self.redis.pipeline()
                
                for jti, exp_timestamp in token_list:
                    # Skip expired tokens
                    if exp_timestamp <= now:
                        logger.debug(f"Skipping expired token: jti={jti}")
                        continue
                    
                    # Calculate TTL
                    ttl = exp_timestamp - now
                    if ttl < 3600:
                        ttl = 3600
                    
                    # Add to blacklist
                    blacklist_key = f"{self.BLACKLIST_PREFIX}:{jti}"
                    pipe.setex(blacklist_key, ttl, "1")
                    
                    # Store metadata
                    metadata_key = f"{self.TOKEN_METADATA_PREFIX}:{jti}"
                    metadata_dict = {
                        "user_id": str(user_id),
                        "reason": reason,
                        "revoked_at": now,
                        "admin_id": str(admin_id) if admin_id else None,
                    }
                    pipe.setex(
                        metadata_key,
                        ttl,
                        json.dumps(metadata_dict, default=str)
                    )
                    
                    revoked_count += 1
                
                # Add all JTIs to user_tokens set
                if revoked_count > 0:
                    user_tokens_key = f"{self.USER_TOKENS_PREFIX}:{user_id}"
                    jtis = [jti for jti, _ in token_list]
                    pipe.sadd(user_tokens_key, *jtis)
                    
                    # Set TTL on user_tokens set
                    max_exp = max(exp for _, exp in token_list)
                    ttl = max(max_exp - now, 3600)
                    pipe.expire(user_tokens_key, ttl)
                
                # Execute pipeline
                await pipe.execute()
                
                logger.info(
                    f"Batch revoked tokens: user_id={user_id}, "
                    f"count={revoked_count}, reason={reason}"
                )
                
                # Record metrics and audit log
                TokenBlacklistMetrics.record_revocation(reason, success=True)
                audit_logger.log_batch_token_revocation(
                    user_id=str(user_id),
                    count=revoked_count,
                    reason=reason,
                    initiator=str(admin_id) if admin_id else None,
                )
                
                return revoked_count

        except RedisConnectionError as e:
            logger.error(f"Redis connection error during batch revocation: {e}")
            RedisMetrics.record_connection_error("revoke_all_user_tokens")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during batch revocation: {e}")
            raise

    async def is_token_revoked(self, token_jti: str) -> bool:
        """
        Check if a token is in the blacklist.
        
        Args:
            token_jti: JWT ID to check
        
        Returns:
            bool: True if token is revoked, False if active
        
        Raises:
            RedisConnectionError: if Redis is unavailable
        
        Performance:
            - O(1) Redis EXISTS operation
            - Latency: <5ms on local Redis
        """
        try:
            blacklist_key = f"{self.BLACKLIST_PREFIX}:{token_jti}"
            exists = await self.redis.exists(blacklist_key)
            
            if exists:
                logger.debug(f"Token found in blacklist: jti={token_jti}")
            
            return bool(exists)

        except RedisConnectionError as e:
            logger.error(f"Redis connection error checking token revocation: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error checking token revocation: {e}")
            raise

    async def get_token_metadata(self, token_jti: str) -> Optional[dict]:
        """
        Get metadata of a revoked token.
        
        Args:
            token_jti: JWT ID
        
        Returns:
            Optional[dict]: Metadata if token is revoked, None otherwise
            
        Structure:
            {
                "user_id": "UUID",
                "reason": "user_deleted | admin_revoke | user_logout",
                "revoked_at": 1711960590,  # Unix timestamp
                "admin_id": "UUID or null"
            }
        """
        try:
            metadata_key = f"{self.TOKEN_METADATA_PREFIX}:{token_jti}"
            metadata_json = await self.redis.get(metadata_key)
            
            if not metadata_json:
                return None
            
            return json.loads(metadata_json)

        except RedisConnectionError as e:
            logger.error(f"Redis connection error getting token metadata: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting token metadata: {e}")
            raise

    async def cleanup_user_tokens(self, user_id: str) -> int:
        """
        Clean up expired tokens from user_tokens set.
        
        This is an optional operation for maintenance. Redis TTL automatically
        cleans up keys, but this function helps clean up expired entries from
        the user_tokens set.
        
        Args:
            user_id: User ID
        
        Returns:
            int: Number of cleaned tokens
        """
        try:
            user_tokens_key = f"{self.USER_TOKENS_PREFIX}:{user_id}"
            
            # Get all JTIs for user
            jtis = await self.redis.smembers(user_tokens_key)
            
            if not jtis:
                return 0
            
            now = int(time.time())
            expired_count = 0
            
            # Check which tokens are no longer in blacklist (expired)
            for jti in jtis:
                blacklist_key = f"{self.BLACKLIST_PREFIX}:{jti}"
                exists = await self.redis.exists(blacklist_key)
                
                if not exists:
                    # Token expired from Redis, remove from set
                    await self.redis.srem(user_tokens_key, jti)
                    expired_count += 1
            
            logger.info(
                f"Cleaned up user tokens: user_id={user_id}, "
                f"cleaned={expired_count}"
            )
            
            return expired_count

        except RedisConnectionError as e:
            logger.error(f"Redis connection error during cleanup: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during cleanup: {e}")
            raise


# Global service instance
_token_blacklist_service: Optional[TokenBlacklistService] = None


async def init_token_blacklist_service(redis: Redis) -> TokenBlacklistService:
    """
    Initialize the token blacklist service with Redis client.
    
    Args:
        redis: Redis client instance
    
    Returns:
        TokenBlacklistService instance
    """
    global _token_blacklist_service
    _token_blacklist_service = TokenBlacklistService(redis)
    logger.info("Token blacklist service initialized")
    return _token_blacklist_service


async def get_token_blacklist_service() -> TokenBlacklistService:
    """
    Get the token blacklist service instance.
    
    Returns:
        TokenBlacklistService instance
    
    Raises:
        RuntimeError: if service not initialized
    """
    if _token_blacklist_service is None:
        raise RuntimeError("Token blacklist service not initialized")
    return _token_blacklist_service
