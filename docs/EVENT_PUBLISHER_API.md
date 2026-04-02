# API Документация: Event Publisher

## Обзор

`RedisStreamsPublisher` — это сервис, который публикует события, связанные с пользователями, в Redis Streams для асинхронной обработки Core Service. Обеспечивает надежную доставку событий с отслеживанием корреляции и автоматической сериализацией полезной нагрузки.

## Класс: RedisStreamsPublisher

### Инициализация

```python
from app.services.event_publisher import RedisStreamsPublisher
from redis import AsyncRedis

# Инициализация с клиентом Redis
redis_client = AsyncRedis(host="redis", port=6379, decode_responses=True)
publisher = RedisStreamsPublisher(redis_client)

# Инициализация потока и конфигурации
await publisher.initialize()
```

#### Параметры конфигурации

- `stream_key` (str): Ключ Redis Stream (по умолчанию: "user_events")
- `max_stream_length` (int): Максимальный размер потока (по умолчанию: 100000)
- `min_chunk_size` (int): Минимальный размер чанка для MAXLEN (по умолчанию: 1000)

### Методы

#### `async initialize()`

Инициализирует издателя и настраивает параметры Redis Stream.

```python
await publisher.initialize()
```

**Возвращает:** `None`

**Исключения:**
- `RedisError`: Если ошибка подключения к Redis
- `RuntimeError`: Если издатель уже инициализирован

#### `async publish_event()`

Публикует одно событие в поток.

```python
event_id = await publisher.publish_event(
    event_type="user.created",
    user_id="550e8400-e29b-41d4-a716-446655440000",
    data={
        "username": "john_doe",
        "email": "john@example.com",
        "is_active": True,
    },
    correlation_id="corr-abc-123",  # Опционально
    causation_id="cause-xyz-789",   # Опционально
)
```

**Параметры:**

| Параметр | Тип | Обязательно | Описание |
|----------|-----|-------------|---------|
| `event_type` | str | Да | Тип события (например, "user.created", "user.updated", "user.deleted") |
| `user_id` | str | Да | ID пользователя (UUID строка) |
| `data` | dict | Да | Данные полезной нагрузки события |
| `correlation_id` | str | Нет | ID корреляции для трассирования запроса |
| `causation_id` | str | Нет | ID причины для отслеживания цепочки событий |

**Возвращает:** `str` - ID события из Redis Stream

**Исключения:**
- `RedisError`: Если публикация не удалась
- `ValueError`: Если event_type некорректен
- `JSONEncodeError`: Если данные не могут быть сериализованы

#### `async publish_user_created()`

Удобный метод для публикации события создания пользователя.

```python
event_id = await publisher.publish_user_created(
    user_id="550e8400-e29b-41d4-a716-446655440000",
    username="john_doe",
    email="john@example.com",
)
```

**Параметры:**

| Параметр | Тип | Обязательно | Описание |
|----------|-----|-------------|---------|
| `user_id` | str | Да | ID пользователя |
| `username` | str | Да | Имя пользователя |
| `email` | str | Да | Email адрес |
| `correlation_id` | str | Нет | ID корреляции |

#### `async publish_user_updated()`

Удобный метод для публикации события обновления пользователя.

```python
event_id = await publisher.publish_user_updated(
    user_id="550e8400-e29b-41d4-a716-446655440000",
    email="newemail@example.com",
    is_active=True,
    updated_fields=["email", "is_active"],
)
```

**Параметры:**

| Параметр | Тип | Обязательно | Описание |
|----------|-----|-------------|---------|
| `user_id` | str | Да | ID пользователя |
| `updated_fields` | dict или list | Да | Поля, которые были обновлены |
| `correlation_id` | str | Нет | ID корреляции |

#### `async publish_user_deleted()`

Удобный метод для публикации события удаления пользователя.

```python
event_id = await publisher.publish_user_deleted(
    user_id="550e8400-e29b-41d4-a716-446655440000",
    username="john_doe",
)
```

**Параметры:**

| Параметр | Тип | Обязательно | Описание |
|----------|-----|-------------|---------|
| `user_id` | str | Да | ID пользователя |
| `username` | str | Нет | Имя пользователя (опционально для аудита) |
| `correlation_id` | str | Нет | ID корреляции |

---

## Структура события

### Конверт события

Все события при публикации в Redis следуют этой структуре:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "user.created",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "version": "1.0",
  "timestamp": "2026-03-31T20:33:12.564Z",
  "correlation_id": "corr-abc-123",
  "causation_id": "cause-xyz-789",
  "data": {
    "username": "john_doe",
    "email": "john@example.com"
  }
}
```

### Типы событий

#### user.created

Публикуется при регистрации нового пользователя.

```python
await publisher.publish_user_created(
    user_id="user-123",
    username="newuser",
    email="new@example.com",
)
```

**Схема данных:**
```json
{
  "user_id": "string",
  "username": "string",
  "email": "string"
}
```

#### user.updated

Публикуется при изменении профиля пользователя.

```python
await publisher.publish_user_updated(
    user_id="user-123",
    email="updated@example.com",
    is_active=False,
    updated_fields=["email", "is_active"],
)
```

**Схема данных:**
```json
{
  "user_id": "string",
  "email": "string (опционально)",
  "is_active": "boolean (опционально)",
  "updated_fields": ["string"]
}
```

#### user.deleted

Публикуется при удалении учетной записи пользователя (мягкое удаление).

```python
await publisher.publish_user_deleted(
    user_id="user-123",
    username="deleteduser",
)
```

**Схема данных:**
```json
{
  "user_id": "string",
  "username": "string (опционально)",
  "deleted_at": "ISO8601 временная метка (опционально)"
}
```

#### token.revoked

Публикуется при отзыве токенов.

```python
await publisher.publish_event(
    event_type="token.revoked",
    user_id="user-123",
    data={
        "jti": "token-jti-value",
        "reason": "logout",
        "count": 1,
    },
)
```

---

## Примеры интеграции

### Пример 1: Публикация события создания пользователя

```python
from app.services.event_publisher import RedisStreamsPublisher
from app.services.user_service import UserService

async def register_user(username: str, email: str, password: str):
    # Создание пользователя в auth service
    user = await user_service.register_user(username, email, password)
    
    # Публикация события создания в core service
    event_id = await publisher.publish_user_created(
        user_id=user.id,
        username=user.username,
        email=user.email,
    )
    
    return {
        "user_id": user.id,
        "event_id": event_id,
    }
```

### Пример 2: Публикация удаления пользователя с отзывом токенов

```python
from app.services.token_blacklist_service import TokenBlacklistService

async def delete_user_with_event(user_id: str, reason: str = "admin_request"):
    # Шаг 1: Отозвать все токены пользователя
    tokens_revoked = await blacklist_service.revoke_all_user_tokens(
        user_id=user_id,
        reason="user_deletion",
    )
    
    # Шаг 2: Отметить пользователя как удаленного в БД
    user = await user_service.get_by_id(user_id)
    user.is_deleted = True
    user.deleted_at = datetime.utcnow()
    user.deletion_reason = reason
    await db.flush()
    
    # Шаг 3: Публикация события удаления
    event_id = await publisher.publish_user_deleted(
        user_id=user.id,
        username=user.username,
        correlation_id=f"deletion-{user_id}",
    )
    
    return {
        "tokens_revoked": tokens_revoked,
        "event_id": event_id,
    }
```

### Пример 3: Отслеживание корреляции

```python
# Трассирование запросов между микросервисами
correlation_id = request.headers.get("X-Correlation-ID")

event_id = await publisher.publish_event(
    event_type="user.updated",
    user_id="user-123",
    data={"email": "new@example.com"},
    correlation_id=correlation_id,
)

# Логирование для аудита
logger.info(f"Event published", extra={
    "event_id": event_id,
    "correlation_id": correlation_id,
    "event_type": "user.updated",
})
```

---

## Обработка ошибок

### Ошибка подключения к Redis

```python
try:
    event_id = await publisher.publish_event(...)
except RedisError as e:
    logger.error("Failed to publish event", exc_info=True)
    # Fallback: сохранить в базе данных для повтора
    await outbox_service.save_event(
        event_type=event_type,
        data=data,
        status="pending",
    )
```

### Некорректные данные события

```python
try:
    event_id = await publisher.publish_event(
        event_type="user.created",
        user_id="user-123",
        data={"non_serializable": lambda x: x},  # Некорректно
    )
except JSONEncodeError as e:
    logger.error("Event data serialization failed", exc_info=True)
```

---

## Конфигурация

### Переменные окружения

```env
# .env
EVENTS_STREAM_KEY=user_events
EVENTS_STREAM_MAXLEN=100000
EVENTS_STREAM_MIN_CHUNK_SIZE=1000
EVENTS_VERSION=1.0
USE_EVENT_PUBLISHING=true
```

### Класс Settings

```python
from app.core.config import Settings

class Settings(BaseSettings):
    events_stream_key: str = "user_events"
    events_stream_maxlen: int = 100000
    events_version: str = "1.0"
    use_event_publishing: bool = True
```

---

## Производительность

### Управление размером потока

Издатель автоматически управляет размером потока используя MAXLEN с приблизительным обрезанием:

```python
# XADD с MAXLEN
# Это сохраняет размер потока в пределах лимита
await redis.xadd(
    "user_events",
    {"data": "..."},
    maxlen=100000,
    approximate=True,  # Разрешает приблизительное обрезание
)
```

### Групповые операции

Для публикации нескольких событий рассмотрите группировку:

```python
async def publish_batch(events: list):
    tasks = [
        publisher.publish_event(
            event_type=event["type"],
            user_id=event["user_id"],
            data=event["data"],
        )
        for event in events
    ]
    event_ids = await asyncio.gather(*tasks)
    return event_ids
```

---

## Мониторинг

### Основные метрики

- `auth_events_published_total`: Всего опубликовано событий (по типу события и статусу)
- `auth_event_publish_duration_seconds`: Задержка публикации события (по типу события)
- `auth_event_stream_size`: Текущий размер потока событий

### Пример Prometheus запроса

```promql
# События опубликованные в секунду
rate(auth_events_published_total[5m])

# P95 задержка публикации
histogram_quantile(0.95, auth_event_publish_duration_seconds_bucket)

# Предупреждение о размере потока
auth_event_stream_size > 90000
```

---

## Связанная документация

- [API Token Blacklist Service](TOKEN_BLACKLIST_API.md)
- [API Event Consumer](../codelab-core-service/docs/EVENT_CONSUMER_API.md)
- [Поток удаления пользователя](../codelab-auth-service/openspec/changes/2026-03-31-implement-user-sync-events/specs/user-deletion-flow/spec.md)
- [Руководство по Redis Streams](../plans/redis-streams-implementation-guide.md)
