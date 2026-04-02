"""Event publisher service for Redis Streams"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from datetime import datetime, timezone

from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.config import logger
from app.services.monitoring import (
    EventPublisherMetrics,
    RedisMetrics,
)


class RedisStreamsPublisher:
    """
    Publisher for sending events to Redis Streams.
    
    Publishes events to other microservices with support for correlation IDs
    and automatic event envelope creation.
    """

    STREAM_KEY = "user_events"
    STREAM_MAXLEN = 100000
    EVENT_VERSION = "1.0"
    SOURCE = "auth-service"

    def __init__(self, redis: Redis):
        """
        Initialize the Redis Streams publisher.
        
        Args:
            redis: Redis client (redis.asyncio.Redis or redis.Redis)
        """
        self.redis = redis

    async def initialize(self) -> None:
        """
        Initialize publisher on startup.
        
        Creates necessary structures in Redis (if needed).
        
        Raises:
            RedisConnectionError: if Redis is unavailable
        """
        try:
            # Test connection
            await self.redis.ping()
            logger.info("Redis Streams Publisher initialized")
        except RedisConnectionError as e:
            logger.error(f"Failed to initialize Redis Streams Publisher: {e}")
            raise

    async def publish_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        data: dict[str, Any],
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
    ) -> str:
        """
        Publish event to Redis Stream.
        
        Args:
            event_type: Type of event (e.g., "user.created", "user.deleted")
            aggregate_type: Type of aggregate (e.g., "user", "token")
            aggregate_id: UUID of the aggregate (user_id, token_id)
            data: Event payload (dict with JSON-serializable values)
            correlation_id: Correlation ID for tracing (optional)
                If not provided, will use event_id
            causation_id: Causation ID for event chain (optional)
                If not provided, will use event_id
        
        Returns:
            str: Redis Stream Message ID (e.g., "1711960590000-0")
        
        Raises:
            RedisConnectionError: if Redis is unavailable
            ValueError: if event_type is empty
            TypeError: if data contains non-serializable objects
        """
        try:
            # Validate inputs
            if not event_type:
                raise ValueError("event_type cannot be empty")
            
            if not isinstance(data, dict):
                raise TypeError("data must be a dict")
            
            # Generate IDs
            event_id = str(uuid.uuid4())
            if not correlation_id:
                correlation_id = event_id
            if not causation_id:
                causation_id = event_id
            
            # Create timestamp
            timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            
            # Create event envelope
            event_envelope = {
                "event_id": event_id,
                "event_type": event_type,
                "event_version": self.EVENT_VERSION,
                "timestamp": timestamp,
                "aggregate_type": aggregate_type,
                "aggregate_id": str(aggregate_id),
                "correlation_id": str(correlation_id),
                "causation_id": str(causation_id),
                "source": self.SOURCE,
                "data": json.dumps(data, default=str),
            }
            
            # Publish to stream
            message_id = await self.redis.xadd(
                self.STREAM_KEY,
                event_envelope,
                maxlen=self.STREAM_MAXLEN,
                approximate=True,
            )
            
            # Convert bytes to string if needed
            if isinstance(message_id, bytes):
                message_id = message_id.decode()
            
            logger.info(
                f"Event published: type={event_type}, "
                f"aggregate_id={aggregate_id}, "
                f"message_id={message_id}, "
                f"event_id={event_id}"
            )
            
            return message_id

        except RedisConnectionError as e:
            logger.error(
                f"Redis connection error during event publication: {e}, "
                f"event_type={event_type}"
            )
            raise
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid event data: {e}, event_type={event_type}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error during event publication: {e}, "
                f"event_type={event_type}"
            )
            raise

    async def publish_user_created(
        self,
        user_id: str,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        created_at: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> str:
        """
        Publish user.created event.
        
        Args:
            user_id: User ID (UUID)
            email: User email
            first_name: User first name (optional)
            last_name: User last name (optional)
            created_at: Creation timestamp (ISO8601, optional)
            correlation_id: Correlation ID for tracing (optional)
        
        Returns:
            str: Message ID
        """
        data = {
            "user_id": str(user_id),
            "email": email,
        }
        
        if first_name:
            data["first_name"] = first_name
        if last_name:
            data["last_name"] = last_name
        if created_at:
            data["created_at"] = created_at
        else:
            data["created_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        return await self.publish_event(
            event_type="user.created",
            aggregate_type="user",
            aggregate_id=user_id,
            data=data,
            correlation_id=correlation_id,
        )

    async def publish_user_updated(
        self,
        user_id: str,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        changes: Optional[list[str]] = None,
        updated_at: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> str:
        """
        Publish user.updated event.
        
        Args:
            user_id: User ID (UUID)
            email: User email (optional)
            first_name: User first name (optional)
            last_name: User last name (optional)
            changes: List of changed fields (optional)
            updated_at: Update timestamp (ISO8601, optional)
            correlation_id: Correlation ID for tracing (optional)
        
        Returns:
            str: Message ID
        """
        data = {
            "user_id": str(user_id),
        }
        
        if email:
            data["email"] = email
        if first_name:
            data["first_name"] = first_name
        if last_name:
            data["last_name"] = last_name
        if changes:
            data["changes"] = changes
        if updated_at:
            data["updated_at"] = updated_at
        else:
            data["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        return await self.publish_event(
            event_type="user.updated",
            aggregate_type="user",
            aggregate_id=user_id,
            data=data,
            correlation_id=correlation_id,
        )

    async def publish_user_deleted(
        self,
        user_id: str,
        email: Optional[str] = None,
        reason: str = "admin_deletion",
        admin_id: Optional[str] = None,
        deleted_at: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> str:
        """
        Publish user.deleted event.
        
        Args:
            user_id: User ID (UUID)
            email: User email (optional)
            reason: Reason for deletion (default: "admin_deletion")
            admin_id: Admin ID if deleted by admin (optional)
            deleted_at: Deletion timestamp (ISO8601, optional)
            correlation_id: Correlation ID for tracing (optional)
        
        Returns:
            str: Message ID
        """
        data = {
            "user_id": str(user_id),
            "reason": reason,
        }
        
        if email:
            data["email"] = email
        if admin_id:
            data["admin_id"] = str(admin_id)
        if deleted_at:
            data["deleted_at"] = deleted_at
        else:
            data["deleted_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        return await self.publish_event(
            event_type="user.deleted",
            aggregate_type="user",
            aggregate_id=user_id,
            data=data,
            correlation_id=correlation_id,
        )

    async def publish_token_revoked(
        self,
        token_jti: str,
        user_id: str,
        reason: str = "user_requested",
        admin_id: Optional[str] = None,
        revoked_at: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> str:
        """
        Publish token.revoked event.
        
        Args:
            token_jti: Token JTI (JWT ID)
            user_id: User ID (UUID)
            reason: Reason for revocation (default: "user_requested")
            admin_id: Admin ID if revoked by admin (optional)
            revoked_at: Revocation timestamp (ISO8601, optional)
            correlation_id: Correlation ID for tracing (optional)
        
        Returns:
            str: Message ID
        """
        data = {
            "token_jti": token_jti,
            "user_id": str(user_id),
            "reason": reason,
        }
        
        if admin_id:
            data["admin_id"] = str(admin_id)
        if revoked_at:
            data["revoked_at"] = revoked_at
        else:
            data["revoked_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        return await self.publish_event(
            event_type="token.revoked",
            aggregate_type="token",
            aggregate_id=token_jti,
            data=data,
            correlation_id=correlation_id,
        )


# Global service instance
_event_publisher: Optional[RedisStreamsPublisher] = None


async def init_event_publisher(redis: Redis) -> RedisStreamsPublisher:
    """
    Initialize the event publisher with Redis client.
    
    Args:
        redis: Redis client instance
    
    Returns:
        RedisStreamsPublisher instance
    """
    global _event_publisher
    _event_publisher = RedisStreamsPublisher(redis)
    await _event_publisher.initialize()
    logger.info("Event publisher initialized")
    return _event_publisher


async def get_event_publisher() -> RedisStreamsPublisher:
    """
    Get the event publisher instance.
    
    Returns:
        RedisStreamsPublisher instance
    
    Raises:
        RuntimeError: if publisher not initialized
    """
    if _event_publisher is None:
        raise RuntimeError("Event publisher not initialized")
    return _event_publisher
