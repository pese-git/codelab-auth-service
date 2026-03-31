# Спецификация: Event Publisher (Redis Streams)

**Версия:** 1.0.0  
**Дата:** 31 марта 2026  
**Сервис:** codelab-auth-service

---

## 📋 Назначение компонента

**EventPublisher** — сервис публикации событий в Redis Streams для уведомления других микросервисов об изменениях в auth-service. Обеспечивает асинхронную, надежную доставку событий между сервисами с поддержкой трассирования (correlation IDs).

### Ключевые функции

- 📤 **Публикация событий** в Redis Stream с автоматическим MAXLEN pruning
- 🔐 **Транзакционная гарантия** — события публикуются только ПОСЛЕ commit в БД
- 🆔 **Correlation IDs** для трассирования запросов через сервисы
- 📝 **Event Envelope** с метаданными (версия, timestamp, source)
- ♻️ **Idempotency** через event_id (для дедупликации потребителем)
- ⏱️ **Event History** (последние 100k событий в памяти)

---

## 🔌 API (Интерфейсы)

### Класс: RedisStreamsPublisher

```python
class RedisStreamsPublisher:
    def __init__(self, redis: Redis):
        """
        Инициализировать publisher
        
        Args:
            redis: Redis async client (redis.asyncio.Redis)
        """
```

### Метод: initialize()

```python
async def initialize(self) -> None:
    """
    Инициализировать publisher на startup
    
    Создает необходимые структуры в Redis (опционально)
    
    Raises:
        RedisConnectionError: если Redis недоступен
    
    Example:
        >>> publisher = RedisStreamsPublisher(redis)
        >>> await publisher.initialize()
    """
```

### Метод: publish_event()

```python
async def publish_event(
    self,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    data: dict[str, Any],
    correlation_id: Optional[str] = None,
    causation_id: Optional[str] = None
) -> str:
    """
    Publish event to Redis Stream
    
    Args:
        event_type (str): Тип события, e.g., "user.created", "user.deleted"
        aggregate_type (str): Тип агрегата, e.g., "user", "token"
        aggregate_id (str): UUID агрегата (user_id, token_id)
        data (dict): Payload события (user info, deleted_at, reason, etc.)
        correlation_id (Optional[str]): Correlation ID для трассирования
            Если не указан, будет использован event_id
        causation_id (Optional[str]): Causation ID для цепочки событий
            Если не указан, будет использован event_id
    
    Returns:
        str: Redis Stream Message ID (e.g., "1711960590000-0")
    
    Raises:
        RedisConnectionError: если Redis недоступен
        ValueError: если event_type пустой
    
    Internals:
        Создает event envelope:
        {
            "event_id": UUID (уникальный),
            "event_type": string,
            "event_version": "1.0",
            "timestamp": ISO8601,
            "aggregate_type": string,
            "aggregate_id": UUID,
            "correlation_id": UUID,
            "causation_id": UUID,
            "source": "auth-service",
            "data": JSON string
        }
        
        XADD user_events event (с MAXLEN ~100000)
    
    Example:
        >>> message_id = await publisher.publish_event(
        ...     event_type="user.deleted",
        ...     aggregate_type="user",
        ...     aggregate_id="123e4567-e89b-12d3-a456-426614174000",
        ...     data={
        ...         "user_id": "123e4567-e89b-12d3-a456-426614174000",
        ...         "email": "user@example.com",
        ...         "reason": "admin_deletion"
        ...     },
        ...     correlation_id="req-12345"
        ... )
        >>> print(f"Message ID: {message_id}")
        Message ID: 1711960590000-0
    """
```

---

## 📊 Схемы данных

### Redis Stream Schema

```
Stream Key: user_events

Message Structure:
{
  "field": "value",
  "field": "value",
  ...
}

Fields (все string values в Redis Streams):
  event_id          : UUID (unique event identifier)
  event_type        : string (e.g., "user.deleted")
  event_version     : string ("1.0")
  timestamp         : ISO8601 string (e.g., "2026-03-31T11:16:30Z")
  aggregate_type    : string ("user", "token", etc.)
  aggregate_id      : UUID (user_id, token_id, etc.)
  correlation_id    : UUID (for request tracing)
  causation_id      : UUID (for event causation chain)
  source            : string ("auth-service")
  data              : JSON string (payload)
```

### Event Types & Payloads

#### Event: user.created

```json
{
  "event_type": "user.created",
  "aggregate_type": "user",
  "aggregate_id": "123e4567-e89b-12d3-a456-426614174000",
  "data": {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "created_at": "2026-03-31T11:16:30Z"
  }
}
```

#### Event: user.updated

```json
{
  "event_type": "user.updated",
  "aggregate_type": "user",
  "aggregate_id": "123e4567-e89b-12d3-a456-426614174000",
  "data": {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "newemail@example.com",
    "first_name": "Jane",
    "last_name": "Smith",
    "updated_at": "2026-03-31T12:00:00Z",
    "changes": ["email", "first_name"]
  }
}
```

#### Event: user.deleted

```json
{
  "event_type": "user.deleted",
  "aggregate_type": "user",
  "aggregate_id": "123e4567-e89b-12d3-a456-426614174000",
  "data": {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "deleted_at": "2026-03-31T12:05:00Z",
    "reason": "admin_deletion",
    "admin_id": "admin-uuid-123"
  }
}
```

---

## 🔄 Примеры использования

### Пример 1: Публикация user.deleted события

```python
from app.services.event_publisher import get_event_publisher
from datetime import datetime, timezone

@router.delete("/admin/users/{user_id}")
async def delete_user(user_id: UUID):
    """Delete user endpoint"""
    
    # Удалить пользователя в БД
    user = await db.delete_user(user_id)
    
    # Опубликовать событие
    publisher = await get_event_publisher()
    event_id = await publisher.publish_event(
        event_type="user.deleted",
        aggregate_type="user",
        aggregate_id=str(user_id),
        data={
            "user_id": str(user_id),
            "email": user.email,
            "deleted_at": datetime.now(timezone.utc).isoformat() + "Z",
            "reason": "admin_deletion"
        }
    )
    
    return {
        "status": "deleted",
        "user_id": str(user_id),
        "event_id": event_id
    }
```

### Пример 2: Публикация с correlation ID (для трассирования)

```python
@router.post("/users")
async def create_user(request: Request, user_data: CreateUserSchema):
    """Create user endpoint"""
    
    # Получить correlation ID из request header (или создать новый)
    correlation_id = request.headers.get("X-Correlation-ID")
    
    # Создать пользователя
    user = await db.create_user(user_data)
    
    # Опубликовать событие с сохранением correlation ID
    publisher = await get_event_publisher()
    event_id = await publisher.publish_event(
        event_type="user.created",
        aggregate_type="user",
        aggregate_id=str(user.id),
        data={
            "user_id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "created_at": user.created_at.isoformat() + "Z"
        },
        correlation_id=correlation_id  # Preserved for tracing
    )
    
    return {
        "status": "created",
        "user_id": str(user.id),
        "event_id": event_id,
        "correlation_id": correlation_id
    }
```

### Пример 3: Обработка ошибок при публикации

```python
async def delete_user_with_error_handling(user_id: UUID):
    """Delete user with proper error handling"""
    
    try:
        # Удалить в БД (уже committed)
        await db.delete_user(user_id)
        
        # Опубликовать событие
        publisher = await get_event_publisher()
        await publisher.publish_event(
            event_type="user.deleted",
            aggregate_type="user",
            aggregate_id=str(user_id),
            data={"user_id": str(user_id)}
        )
    
    except RedisConnectionError:
        # Redis недоступен, но удаление уже произошло в БД
        logger.error(
            "event_publish_failed_redis_unavailable",
            user_id=user_id
        )
        # Event может быть переопубликован позже из reconciliation job
        # НЕ откатываем удаление
        raise
    except Exception as e:
        logger.error("event_publish_error", user_id=user_id, error=str(e))
        raise
```

---

## ⚠️ Обработка ошибок

### Сценарий 1: Redis недоступен при публикации

```python
try:
    message_id = await publisher.publish_event(...)
except RedisConnectionError as e:
    logger.error("redis_connection_error_during_publish", error=str(e))
    # БД транзакция уже committed, но событие не опубликовано
    # Стратегия: 
    #   1. Логировать и отправить alert
    #   2. Retry в background job (будущее)
    #   3. Синхронизировать позже через reconciliation
    raise
```

### Сценарий 2: Исключение при подготовке payload

```python
try:
    # data может содержать non-serializable объекты
    await publisher.publish_event(
        event_type="user.updated",
        aggregate_type="user",
        aggregate_id=str(user_id),
        data=user_object  # ❌ ОШИБКА: user_object не JSON-serializable
    )
except TypeError as e:
    logger.error("event_data_serialization_error", error=str(e))
    # Убедиться что data — dict с JSON-serializable значениями
    raise
```

### Сценарий 3: Partial failure при MAXLEN pruning

```python
# Redis Streams автоматически удаляет старые сообщения
# при достижении MAXLEN (~100000)
# Это может привести к потере очень старых событий
# Стратегия: мониторить длину stream, alert если близко к лимиту

redis = await get_redis()
stream_len = await redis.xlen("user_events")
if stream_len > 95000:  # Near limit
    logger.warning("stream_approaching_maxlen", current_length=stream_len)
    # Может потребоваться ручное вмешательство или увеличение MAXLEN
```

---

## 🧪 Тесты

### Unit Test 1: Успешная публикация

```python
@pytest.mark.asyncio
async def test_publish_event_success(publisher):
    """Test successful event publication"""
    
    message_id = await publisher.publish_event(
        event_type="user.deleted",
        aggregate_type="user",
        aggregate_id="user-123",
        data={
            "user_id": "user-123",
            "email": "user@example.com",
            "reason": "admin_deletion"
        }
    )
    
    assert message_id is not None
    assert isinstance(message_id, str)
    assert "-" in message_id  # Redis stream ID format
```

### Unit Test 2: Correlation ID preservation

```python
@pytest.mark.asyncio
async def test_correlation_id_preserved(publisher, redis):
    """Test correlation ID is preserved in event"""
    
    correlation_id = "req-12345-67890"
    
    await publisher.publish_event(
        event_type="user.created",
        aggregate_type="user",
        aggregate_id="user-123",
        data={"user_id": "user-123"},
        correlation_id=correlation_id
    )
    
    # Read from stream and verify
    events = await redis.xread({"user_events": "0"}, count=1)
    event_data = dict(events[0][1][0][1])
    
    assert event_data[b"correlation_id"].decode() == correlation_id
```

### Integration Test 1: Multiple events with MAXLEN

```python
@pytest.mark.asyncio
async def test_maxlen_pruning(publisher):
    """Test MAXLEN pruning works"""
    
    # Publish 1000+ events
    for i in range(1010):
        await publisher.publish_event(
            event_type="user.created",
            aggregate_type="user",
            aggregate_id=f"user-{i}",
            data={"user_id": f"user-{i}"}
        )
    
    # Verify stream length doesn't exceed MAXLEN
    stream_len = await redis.xlen("user_events")
    assert stream_len <= 100000 + 100  # Some tolerance for async operations
```

---

## 📋 Acceptance Criteria

- ✅ `publish_event()` успешно добавляет событие в stream
- ✅ Возвращает message ID в формате Redis Stream
- ✅ Event envelope содержит все требуемые поля
- ✅ Correlation IDs сохраняются и передаются между сервисами
- ✅ MAXLEN pruning работает (старые события удаляются)
- ✅ Ошибки Redis не падают (graceful degradation)
- ✅ Logging: каждая публикация залогирована
- ✅ Performance: publish < 50ms latency (p95)
- ✅ Unit тесты: 100% coverage
- ✅ События доступны для чтения в core-service

---

## 🔗 Связанные компоненты

- [`EventConsumer`](../event-consumer/spec.md) — потребитель в core-service
- [`TokenBlacklistService`](../token-blacklist-service/spec.md) — для публикации при revoke
- [`UserDeletionFlow`](../user-deletion-flow/spec.md) — использует publisher
