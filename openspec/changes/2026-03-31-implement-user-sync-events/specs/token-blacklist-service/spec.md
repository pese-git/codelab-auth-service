# Спецификация: TokenBlacklistService

**Версия:** 1.0.0  
**Дата:** 31 марта 2026  
**Сервис:** codelab-auth-service

---

## 📋 Назначение компонента

**TokenBlacklistService** — сервис управления черным списком (blacklist) отозванных JWT токенов. Обеспечивает немедленную инвалидацию токенов при удалении пользователя или выходе из системы, предотвращая их дальнейшее использование в core-service.

### Ключевые функции

- 🔐 **Отзыв отдельного токена** — SETEX в Redis с TTL
- 🔐 **Batch отзыв всех токенов пользователя** — pipeline операция
- 🔍 **Проверка если токен отозван** — EXISTS в Redis (O(1))
- 📝 **Сохранение метаданных отзыва** — JSON с причиной, администратором, временем
- ⏱️ **Автоматическая очистка** — TTL в Redis

---

## 🔌 API (Интерфейсы)

### Класс: TokenBlacklistService

```python
class TokenBlacklistService:
    def __init__(self, redis: Redis):
        """
        Инициализировать сервис
        
        Args:
            redis: Redis async client (redis.asyncio.Redis)
        """
```

### Метод: revoke_token()

```python
async def revoke_token(
    self,
    token_jti: str,
    user_id: str,
    exp_timestamp: int,
    reason: str = "user_requested",
    admin_id: Optional[str] = None,
    metadata: Optional[dict] = None
) -> bool:
    """
    Отозвать один токен
    
    Args:
        token_jti (str): JWT ID из token payload (jti claim)
        user_id (str): User ID (sub claim в токене)
        exp_timestamp (int): Unix timestamp истечения токена (exp claim)
        reason (str): Причина отзыва:
            - "user_requested" — пользователь запросил (logout)
            - "user_deleted" — пользователь удален
            - "admin_revoke" — администратор отозвал
        admin_id (Optional[str]): UUID администратора если admin_revoke
        metadata (Optional[dict]): Дополнительные метаданные (опционально)
    
    Returns:
        bool: True если токен успешно отозван, False если уже истекал
    
    Raises:
        RedisConnectionError: если Redis недоступен
        ValueError: если exp_timestamp в прошлом
    
    Example:
        >>> service = TokenBlacklistService(redis)
        >>> result = await service.revoke_token(
        ...     token_jti="550e8400-e29b-41d4-a716-446655440000",
        ...     user_id="123e4567-e89b-12d3-a456-426614174000",
        ...     exp_timestamp=1711960590,
        ...     reason="user_deleted",
        ...     admin_id="admin-uuid"
        ... )
        >>> assert result == True
    """
```

### Метод: revoke_all_user_tokens()

```python
async def revoke_all_user_tokens(
    self,
    user_id: str,
    token_list: list[tuple[str, int]],
    reason: str = "user_deleted",
    admin_id: Optional[str] = None
) -> int:
    """
    Отозвать ВСЕ активные токены пользователя за одну операцию
    
    Args:
        user_id (str): User ID
        token_list (list[tuple[str, int]]): Список кортежей (jti, exp_timestamp)
        reason (str): Причина отзыва
        admin_id (Optional[str]): UUID администратора
    
    Returns:
        int: Количество успешно отозванных токенов
    
    Raises:
        RedisConnectionError: если Redis недоступен
    
    Example:
        >>> token_list = [
        ...     ("jti-1", 1711960590),
        ...     ("jti-2", 1711960700),
        ...     ("jti-3", 1711960800),
        ... ]
        >>> count = await service.revoke_all_user_tokens(
        ...     user_id="123e4567-e89b-12d3-a456-426614174000",
        ...     token_list=token_list,
        ...     reason="user_deleted"
        ... )
        >>> assert count == 3
    """
```

### Метод: is_token_revoked()

```python
async def is_token_revoked(self, token_jti: str) -> bool:
    """
    Проверить если токен отозван (в blacklist)
    
    Args:
        token_jti (str): JWT ID для проверки
    
    Returns:
        bool: True если токен отозван, False если активен
    
    Raises:
        RedisConnectionError: если Redis недоступен
    
    Performance:
        - O(1) Redis EXISTS
        - Latency: <5ms на local Redis
    
    Example:
        >>> is_revoked = await service.is_token_revoked(
        ...     "550e8400-e29b-41d4-a716-446655440000"
        ... )
        >>> if is_revoked:
        ...     raise HTTPException(status_code=401, detail="Token revoked")
    """
```

### Метод: get_token_metadata()

```python
async def get_token_metadata(self, token_jti: str) -> Optional[dict]:
    """
    Получить метаданные отозванного токена
    
    Args:
        token_jti (str): JWT ID
    
    Returns:
        Optional[dict]: Метаданные если токен отозван, None иначе
    
    Structure:
        {
            "user_id": "UUID",
            "reason": "user_deleted | admin_revoke | user_logout",
            "revoked_at": 1711960590,  # Unix timestamp
            "admin_id": "UUID или null"
        }
    
    Example:
        >>> metadata = await service.get_token_metadata("jti-123")
        >>> if metadata:
        ...     print(f"Revoked by: {metadata['admin_id']}")
    """
```

### Метод: cleanup_user_tokens()

```python
async def cleanup_user_tokens(self, user_id: str) -> int:
    """
    Очистить expired токены из user_tokens set
    (опциональная операция для maintenance)
    
    Args:
        user_id (str): User ID
    
    Returns:
        int: Количество удаленных токенов из set
    
    Note:
        Это опциональная операция. Redis TTL автоматически очищает
        ключи, поэтому эта функция нужна только для cleanup expired
        записей из user_tokens set.
    """
```

---

## 📊 Схемы данных

### Redis Key Structure

```
# Основной blacklist ключ (TTL = exp - now)
token_blacklist:{jti}
  Type: String
  Value: "1"  (просто флаг)
  TTL: Unix timestamp - current time (в секундах)
  Example: token_blacklist:550e8400-e29b-41d4-a716-446655440000

# User tokens set для быстрого отзыва всех
user_tokens:{user_id}
  Type: Set
  Members: [jti1, jti2, jti3, ...]
  TTL: max(exp_timestamp) - current time
  Example: user_tokens:123e4567-e89b-12d3-a456-426614174000

# Метаданные отзыва (опционально)
token_metadata:{jti}
  Type: String (JSON)
  Value: {
    "user_id": "UUID",
    "reason": "user_deleted",
    "revoked_at": 1711960590,
    "admin_id": "UUID | null",
    "custom_field": "value"
  }
  TTL: exp - now
  Example: token_metadata:550e8400-e29b-41d4-a716-446655440000
```

### JSON Payload Examples

#### Пример 1: Отзыв при logout

```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "token_jti": "550e8400-e29b-41d4-a716-446655440000",
  "exp_timestamp": 1711960590,
  "reason": "user_requested",
  "admin_id": null,
  "revoked_at": 1711957000
}
```

#### Пример 2: Отзыв при удалении пользователя

```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "token_jti": "550e8400-e29b-41d4-a716-446655440000",
  "exp_timestamp": 1711960590,
  "reason": "user_deleted",
  "admin_id": null,
  "revoked_at": 1711957000
}
```

#### Пример 3: Batch revoke при admin action

```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "token_list": [
    ["jti-1", 1711960590],
    ["jti-2", 1711960700],
    ["jti-3", 1711960800]
  ],
  "reason": "admin_revoke",
  "admin_id": "admin-uuid-123",
  "revoked_at": 1711957000,
  "total_revoked": 3
}
```

---

## 🔄 Примеры использования

### Пример 1: Logout (пользователь выходит)

```python
from app.services.token_blacklist_service import get_token_blacklist_service

@router.post("/logout")
async def logout(request: Request):
    """Logout endpoint — отозвать текущий токен"""
    
    user_id = request.state.user_id
    token_jti = request.state.token_jti  # Извлечено из middleware
    token_exp = request.state.token_exp  # Извлечено из JWT
    
    blacklist_service = await get_token_blacklist_service()
    
    success = await blacklist_service.revoke_token(
        token_jti=token_jti,
        user_id=str(user_id),
        exp_timestamp=token_exp,
        reason="user_requested"
    )
    
    return {
        "status": "logged_out",
        "token_revoked": success
    }
```

### Пример 2: Cascade delete при удалении пользователя

```python
from app.services.token_blacklist_service import get_token_blacklist_service
from sqlalchemy import select
from app.models.token import RefreshToken

async def delete_user(user_id: UUID, session: AsyncSession):
    """Delete user — отозвать все его токены"""
    
    # Получить все активные токены
    result = await session.execute(
        select(RefreshToken).where(
            (RefreshToken.user_id == user_id) &
            (RefreshToken.exp > datetime.now(timezone.utc))
        )
    )
    tokens = result.scalars().all()
    
    # Подготовить список для batch revoke
    token_list = [
        (t.jti, int(t.exp.timestamp()))
        for t in tokens
    ]
    
    # Отозвать все токены
    blacklist_service = await get_token_blacklist_service()
    revoked_count = await blacklist_service.revoke_all_user_tokens(
        user_id=str(user_id),
        token_list=token_list,
        reason="user_deleted"
    )
    
    # Удалить пользователя в БД
    await session.delete(user)
    await session.commit()
    
    logger.info(f"User deleted: {user_id}, tokens revoked: {revoked_count}")
    
    return revoked_count
```

### Пример 3: Middleware проверка токена

```python
from app.middleware.user_isolation import UserIsolationMiddleware
from app.services.token_blacklist_service import get_token_blacklist_service

class UserIsolationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Извлечь и валидировать JWT
        token = extract_token(request)
        payload = await validate_jwt(token)
        
        token_jti = payload.get("jti")
        
        # Проверить если в blacklist
        blacklist_service = await get_token_blacklist_service()
        is_revoked = await blacklist_service.is_token_revoked(token_jti)
        
        if is_revoked:
            return JSONResponse(
                status_code=401,
                content={"error": "Token has been revoked"}
            )
        
        # Токен OK, продолжить обработку
        request.state.user_id = UUID(payload["sub"])
        request.state.token_jti = token_jti
        
        response = await call_next(request)
        return response
```

---

## ⚠️ Обработка ошибок

### Сценарий 1: Redis недоступен

```python
try:
    is_revoked = await blacklist_service.is_token_revoked(jti)
except RedisConnectionError:
    logger.error("redis_unavailable_for_blacklist_check")
    # Fallback: rely only on JWT exp claim
    # Риск: токен может быть использован до истечения
    is_revoked = False
    # ⚠️ ALERT: должна быть отправлена в мониторинг
```

### Сценарий 2: Batch revoke с partial success

```python
try:
    revoked = await service.revoke_all_user_tokens(
        user_id=user_id,
        token_list=token_list
    )
except Exception as e:
    logger.error(f"batch_revoke_error: {e}")
    # Tokens might be partially revoked
    # Retry logic должна быть в caller
    raise
```

### Сценарий 3: Токен уже истек

```python
success = await service.revoke_token(
    token_jti=jti,
    user_id=user_id,
    exp_timestamp=1000000  # В прошлом!
)
# Returns: False (токен уже мертв)
```

---

## 🧪 Тесты

### Unit Test 1: Успешный revoke

```python
@pytest.mark.asyncio
async def test_revoke_token_success(blacklist_service):
    """Test revoking a single token"""
    user_id = "user-123"
    jti = "token-456"
    exp = int(time.time()) + 3600
    
    result = await blacklist_service.revoke_token(
        token_jti=jti,
        user_id=user_id,
        exp_timestamp=exp,
        reason="user_logout"
    )
    
    assert result == True
    
    # Verify it's revoked
    is_revoked = await blacklist_service.is_token_revoked(jti)
    assert is_revoked == True
```

### Unit Test 2: TTL автоматически очищает

```python
@pytest.mark.asyncio
async def test_token_expires_from_blacklist(blacklist_service):
    """Test that expired tokens are automatically cleaned"""
    user_id = "user-123"
    jti = "token-456"
    exp = int(time.time()) + 2  # 2 seconds
    
    # Revoke with short TTL
    await blacklist_service.revoke_token(
        token_jti=jti,
        user_id=user_id,
        exp_timestamp=exp
    )
    
    # Verify revoked now
    assert await blacklist_service.is_token_revoked(jti) == True
    
    # Wait for TTL to expire
    await asyncio.sleep(3)
    
    # Verify cleaned up
    assert await blacklist_service.is_token_revoked(jti) == False
```

### Integration Test 1: Batch revoke

```python
@pytest.mark.asyncio
async def test_revoke_all_user_tokens(blacklist_service):
    """Test batch revoke"""
    user_id = "user-123"
    now = int(time.time())
    
    token_list = [
        ("jti-1", now + 3600),
        ("jti-2", now + 7200),
        ("jti-3", now + 10800),
    ]
    
    count = await blacklist_service.revoke_all_user_tokens(
        user_id=user_id,
        token_list=token_list
    )
    
    assert count == 3
    
    for jti, _ in token_list:
        assert await blacklist_service.is_token_revoked(jti) == True
```

---

## 📋 Acceptance Criteria

- ✅ `revoke_token()` создает ключ в Redis с правильным TTL
- ✅ `revoke_all_user_tokens()` отзывает batch токенов (pipeline)
- ✅ `is_token_revoked()` возвращает TRUE для отозванных, FALSE для активных
- ✅ TTL автоматически очищает expired ключи
- ✅ Метаданные сохраняются и читаются корректно
- ✅ Error handling: graceful degradation если Redis down
- ✅ Logging: каждая операция залогирована с нужным уровнем
- ✅ Performance: `is_token_revoked()` < 5ms latency (p95)
- ✅ Unit тесты: 100% coverage TokenBlacklistService
- ✅ Нет потери данных при перезагрузке Redis (persistence)
