"""Monitoring and metrics service for auth microservice."""

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Callable, Optional

from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)


# ============================================================================
# Prometheus Metrics
# ============================================================================

# Token Blacklist Metrics
token_revocations_total = Counter(
    "auth_token_revocations_total",
    "Total number of token revocations",
    ["reason", "status"],
)

token_revocation_duration_seconds = Histogram(
    "auth_token_revocation_duration_seconds",
    "Time taken to revoke tokens in seconds",
    ["operation"],
)

blacklist_check_total = Counter(
    "auth_blacklist_check_total",
    "Total number of blacklist checks",
    ["status"],
)

blacklist_check_duration_seconds = Histogram(
    "auth_blacklist_check_duration_seconds",
    "Time taken to check if token is blacklisted in seconds",
)

active_blacklisted_tokens = Gauge(
    "auth_active_blacklisted_tokens",
    "Current number of blacklisted tokens in Redis",
)

# Event Publisher Metrics
events_published_total = Counter(
    "auth_events_published_total",
    "Total number of events published",
    ["event_type", "status"],
)

event_publish_duration_seconds = Histogram(
    "auth_event_publish_duration_seconds",
    "Time taken to publish event in seconds",
    ["event_type"],
)

event_stream_size = Gauge(
    "auth_event_stream_size",
    "Current size of event stream",
)

# Redis Connection Metrics
redis_connection_errors_total = Counter(
    "auth_redis_connection_errors_total",
    "Total number of Redis connection errors",
    ["operation"],
)

redis_operation_duration_seconds = Histogram(
    "auth_redis_operation_duration_seconds",
    "Time taken for Redis operation in seconds",
    ["operation"],
)


# ============================================================================
# Monitoring Utilities
# ============================================================================

class TokenBlacklistMetrics:
    """Metrics collection for token blacklist operations."""

    @staticmethod
    def record_revocation(reason: str, success: bool = True):
        """Record token revocation metric."""
        status = "success" if success else "failure"
        token_revocations_total.labels(reason=reason, status=status).inc()
        logger.info(
            "Token revocation recorded",
            extra={
                "event": "token_revocation",
                "reason": reason,
                "status": status,
            },
        )

    @staticmethod
    @asynccontextmanager
    async def measure_revocation(operation: str):
        """Context manager to measure revocation operation duration."""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            token_revocation_duration_seconds.labels(operation=operation).observe(
                duration
            )
            logger.debug(
                "Revocation operation completed",
                extra={
                    "event": "revocation_operation_complete",
                    "operation": operation,
                    "duration_seconds": duration,
                },
            )

    @staticmethod
    def record_blacklist_check(is_revoked: bool):
        """Record blacklist check metric."""
        status = "revoked" if is_revoked else "active"
        blacklist_check_total.labels(status=status).inc()

    @staticmethod
    @asynccontextmanager
    async def measure_blacklist_check():
        """Context manager to measure blacklist check duration."""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            blacklist_check_duration_seconds.observe(duration)

    @staticmethod
    def set_active_tokens_count(count: int):
        """Set gauge for active blacklisted tokens count."""
        active_blacklisted_tokens.set(count)
        logger.debug(
            "Blacklist tokens count updated",
            extra={
                "event": "blacklist_tokens_count",
                "count": count,
            },
        )


class EventPublisherMetrics:
    """Metrics collection for event publisher operations."""

    @staticmethod
    def record_event_published(event_type: str, success: bool = True):
        """Record event publication metric."""
        status = "success" if success else "failure"
        events_published_total.labels(event_type=event_type, status=status).inc()
        logger.info(
            "Event published",
            extra={
                "event": "event_published",
                "event_type": event_type,
                "status": status,
            },
        )

    @staticmethod
    @asynccontextmanager
    async def measure_publish(event_type: str):
        """Context manager to measure event publish duration."""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            event_publish_duration_seconds.labels(event_type=event_type).observe(
                duration
            )
            logger.debug(
                "Event publish completed",
                extra={
                    "event": "event_publish_complete",
                    "event_type": event_type,
                    "duration_seconds": duration,
                },
            )

    @staticmethod
    def set_stream_size(size: int):
        """Set gauge for event stream size."""
        event_stream_size.set(size)
        logger.debug(
            "Event stream size updated",
            extra={
                "event": "stream_size",
                "size": size,
            },
        )


class RedisMetrics:
    """Metrics collection for Redis operations."""

    @staticmethod
    def record_connection_error(operation: str):
        """Record Redis connection error."""
        redis_connection_errors_total.labels(operation=operation).inc()
        logger.error(
            "Redis connection error",
            extra={
                "event": "redis_error",
                "operation": operation,
            },
        )

    @staticmethod
    @asynccontextmanager
    async def measure_redis_operation(operation: str):
        """Context manager to measure Redis operation duration."""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            redis_operation_duration_seconds.labels(operation=operation).observe(
                duration
            )
            logger.debug(
                "Redis operation completed",
                extra={
                    "event": "redis_operation_complete",
                    "operation": operation,
                    "duration_seconds": duration,
                },
            )


# ============================================================================
# Logging Utilities
# ============================================================================

class StructuredLogger:
    """Structured logging helper with correlation context."""

    def __init__(self, name: str):
        """Initialize logger."""
        self.logger = logging.getLogger(name)
        self._correlation_id: Optional[str] = None
        self._request_id: Optional[str] = None

    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for request tracing."""
        self._correlation_id = correlation_id

    def set_request_id(self, request_id: str):
        """Set request ID for tracing."""
        self._request_id = request_id

    def _add_context(self, extra: dict) -> dict:
        """Add correlation context to extra fields."""
        if self._correlation_id:
            extra["correlation_id"] = self._correlation_id
        if self._request_id:
            extra["request_id"] = self._request_id
        extra["timestamp"] = datetime.utcnow().isoformat()
        return extra

    def info(self, message: str, **kwargs):
        """Log info message with context."""
        extra = self._add_context(kwargs.get("extra", {}))
        self.logger.info(message, extra=extra)

    def error(self, message: str, **kwargs):
        """Log error message with context."""
        extra = self._add_context(kwargs.get("extra", {}))
        self.logger.error(message, extra=extra, exc_info=kwargs.get("exc_info", False))

    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        extra = self._add_context(kwargs.get("extra", {}))
        self.logger.warning(message, extra=extra)

    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        extra = self._add_context(kwargs.get("extra", {}))
        self.logger.debug(message, extra=extra)


def create_logger(name: str) -> StructuredLogger:
    """Create a structured logger instance."""
    return StructuredLogger(name)


# ============================================================================
# Audit Logging
# ============================================================================

class AuditLogger:
    """Audit logging for security-sensitive operations."""

    def __init__(self):
        """Initialize audit logger."""
        self.logger = logging.getLogger("audit")

    def log_token_revocation(
        self,
        user_id: str,
        jti: str,
        reason: str,
        initiator: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        """Log token revocation audit event."""
        audit_event = {
            "event_type": "token_revocation",
            "user_id": user_id,
            "jti": jti[:20] + "***",  # Redact JTI
            "reason": reason,
            "initiator": initiator or "system",
            "timestamp": datetime.utcnow().isoformat(),
        }
        if metadata:
            audit_event["metadata"] = metadata

        self.logger.info(
            "Token revocation",
            extra=audit_event,
        )

    def log_batch_token_revocation(
        self,
        user_id: str,
        count: int,
        reason: str,
        initiator: Optional[str] = None,
    ):
        """Log batch token revocation audit event."""
        audit_event = {
            "event_type": "batch_token_revocation",
            "user_id": user_id,
            "count": count,
            "reason": reason,
            "initiator": initiator or "system",
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.logger.info(
            "Batch token revocation",
            extra=audit_event,
        )

    def log_user_deletion(
        self,
        user_id: str,
        username: str,
        tokens_revoked: int,
        event_published: bool,
        initiator: Optional[str] = None,
    ):
        """Log user deletion audit event."""
        audit_event = {
            "event_type": "user_deletion",
            "user_id": user_id,
            "username": username,
            "tokens_revoked": tokens_revoked,
            "event_published": event_published,
            "initiator": initiator,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.logger.warning(
            "User deletion",
            extra=audit_event,
        )

    def log_redis_failure(
        self,
        operation: str,
        error: str,
        user_id: Optional[str] = None,
    ):
        """Log Redis operation failure."""
        audit_event = {
            "event_type": "redis_failure",
            "operation": operation,
            "error": str(error),
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.logger.error(
            "Redis operation failed",
            extra=audit_event,
        )


audit_logger = AuditLogger()


# ============================================================================
# Health Check Metrics
# ============================================================================

class HealthCheckMetrics:
    """Metrics for health checks."""

    redis_healthy = Gauge(
        "auth_redis_healthy",
        "Redis connection health (1=healthy, 0=unhealthy)",
    )

    database_healthy = Gauge(
        "auth_database_healthy",
        "Database connection health (1=healthy, 0=unhealthy)",
    )

    @staticmethod
    def set_redis_health(healthy: bool):
        """Update Redis health status."""
        HealthCheckMetrics.redis_healthy.set(1 if healthy else 0)

    @staticmethod
    def set_database_health(healthy: bool):
        """Update database health status."""
        HealthCheckMetrics.database_healthy.set(1 if healthy else 0)
