# Refresh Token Flow Guide

## Обзор

Этот документ описывает полную реализацию механизма refresh token в CodeLab Auth Service, включая:
- OAuth 2.0 refresh token grant flow
- Автоматическую ротацию токенов
- Управление сессиями (multi-device support)
- Детектирование переиспользования токенов
- API endpoints для управления сессиями

## OAuth 2.0 Refresh Token Flow

### 1. Аутентификация по паролю (Password Grant)

```bash
curl -X POST http://localhost:8000/api/v1/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=my-client" \
  -d "username=user@example.com" \
  -d "password=securepassword" \
  -d "scope=read write"
```

**Ответ:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900,
  "scope": "read write",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Описание полей:**
- `access_token`: JWT токен доступа (действителен 15 минут)
- `refresh_token`: JWT токен для обновления доступа (действителен 30 дней)
- `token_type`: Тип токена (всегда "bearer")
- `expires_in`: Время жизни access token в секундах
- `scope`: Запрошенные и выданные scopes
- `session_id`: Уникальный идентификатор сессии (для управления на разных устройствах)

### 2. Обновление токена (Refresh Token Grant)

Когда access token истекает, клиент может получить новый, используя refresh token:

```bash
curl -X POST http://localhost:8000/api/v1/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "client_id=my-client" \
  -d "refresh_token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Ответ:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900,
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Важно:** 
- Новый refresh token выдаётся вместо использованного
- Старый refresh token автоматически отзывается
- Сохраняется session_id для отслеживания цепи токенов
- Это позволяет обнаружить переиспользование токена (security feature)

## Управление сессиями

### 1. Просмотр активных сессий

```bash
curl -X GET http://localhost:8000/api/v1/oauth/sessions \
  -H "Authorization: Bearer <access_token>"
```

**Ответ:**
```json
{
  "sessions": [
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "client_id": "my-client",
      "created_at": "2026-03-25T14:00:00Z",
      "last_used": "2026-03-25T14:45:00Z",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
      "expires_at": "2026-04-24T14:00:00Z"
    },
    {
      "session_id": "660e8400-e29b-41d4-a716-446655440001",
      "client_id": "my-client",
      "created_at": "2026-03-24T10:00:00Z",
      "last_used": "2026-03-25T10:00:00Z",
      "ip_address": "192.168.1.101",
      "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6)...",
      "expires_at": "2026-04-23T10:00:00Z"
    }
  ]
}
```

**Описание:**
- `session_id`: Уникальный идентификатор сессии
- `client_id`: OAuth клиент, который создал сессию
- `created_at`: Время создания сессии
- `last_used`: Время последнего использования токена
- `ip_address`: IP адрес клиента (для справки)
- `user_agent`: User-Agent клиента (для идентификации устройства)
- `expires_at`: Время истечения refresh token

### 2. Получение деталей сессии

```bash
curl -X GET http://localhost:8000/api/v1/oauth/sessions/{session_id} \
  -H "Authorization: Bearer <access_token>"
```

**Ответ:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "client_id": "my-client",
  "scope": "read write",
  "created_at": "2026-03-25T14:00:00Z",
  "last_used": "2026-03-25T14:45:00Z",
  "last_rotated_at": "2026-03-25T14:45:00Z",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
  "expires_at": "2026-04-24T14:00:00Z"
}
```

### 3. Отзыв конкретной сессии

```bash
curl -X DELETE http://localhost:8000/api/v1/oauth/sessions/{session_id} \
  -H "Authorization: Bearer <access_token>"
```

**Ответ:**
```json
{
  "message": "Session 550e8400-e29b-41d4-a716-446655440000 revoked successfully"
}
```

### 4. Выход из всех сессий

```bash
curl -X POST http://localhost:8000/api/v1/oauth/logout \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"all_sessions": true}'
```

**Ответ:**
```json
{
  "message": "Logged out from all sessions (2 sessions revoked)",
  "revoked_count": 2
}
```

### 5. Выход из текущей сессии

```bash
curl -X POST http://localhost:8000/api/v1/oauth/logout \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"all_sessions": false}'
```

**Ответ:**
```json
{
  "message": "Logged out successfully"
}
```

## Стратегия ротации токенов

### Как это работает

1. **Клиент получает токены** через password grant:
   - Access token (15 мин)
   - Refresh token (30 дней)
   - Session ID

2. **Access token истекает**, клиент отправляет refresh token:
   - Сервер проверяет refresh token в БД
   - Если валиден → выдаёт новые токены
   - Старый refresh token отзывается
   - Новый токен сохраняется со ссылкой на старый (parent_jti_hash)

3. **Цепь токенов отслеживается**:
   - Каждый refresh token содержит хеш родительского токена
   - Если обнаружено переиспользование старого токена → отзывается вся цепь

### Преимущества

- **Безопасность**: Если refresh token скомпрометирован, можно обнаружить реиспользование и отозвать все токены
- **Удобство**: Access token живёт только 15 минут, снижая риск
- **Долгоживущесть**: Refresh token живёт 30 дней, но может быть ротирован при каждом использовании
- **Multi-device**: Каждое устройство/сессия имеет свой токен и session_id

## Детектирование переиспользования токена

### Сценарий атаки

1. Злоумышленник перехватывает refresh token
2. Использует его для получения новых токенов
3. Легитимный пользователь также пытается использовать свой старый token
4. Сервер обнаруживает: старый токен используется повторно
5. **Все токены цепи отзываются** (SECURITY: Refresh token reuse detected!)

### Защита

```python
# В RefreshTokenService.validate_refresh_token()
if token.revoked:
    # SECURITY: Refresh token reuse detected!
    logger.warning(f"SECURITY: Refresh token reuse detected!")
    await self.revoke_token_chain(db, token)
    return False, "Refresh token has been revoked (reuse detected)"
```

## Best Practices

### Для фронтенда

1. **Сохраняйте токены безопасно**:
   - Access token: В памяти или localStorage
   - Refresh token: В httpOnly cookie (предпочтительно)

2. **Используйте access token**:
   ```bash
   Authorization: Bearer <access_token>
   ```

3. **Обновляйте токены автоматически**:
   - При истечении access token
   - Или перед каждым запросом (заранее)

4. **Обрабатывайте 401 ошибку**:
   ```javascript
   if (response.status === 401) {
     // Попытайтесь обновить токен
     // Если успешно - повторите запрос
     // Иначе - перенаправьте на логин
   }
   ```

5. **Логируйтесь из всех сессий при смене пароля**:
   ```bash
   POST /api/v1/oauth/logout {"all_sessions": true}
   ```

### Для сервера

1. **Проверяйте access token на каждый запрос**:
   ```python
   payload = auth_svc.validate_token(access_token)
   if not payload:
       raise HTTPException(status_code=401)
   ```

2. **Логируйте операции**:
   - Успешные логины
   - Обновления токенов
   - Обнаруженные переиспользования

3. **Очищайте истёкшие токены**:
   ```python
   await refresh_token_service.cleanup_expired_tokens(db, days_to_keep=7)
   ```

4. **Мониторьте подозрительную активность**:
   - Много попыток с одного IP
   - Одновременное использование разных session_id одним пользователем
   - Rapid refresh token rotation

## Примеры интеграции

### JavaScript/TypeScript

```typescript
class AuthClient {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private sessionId: string | null = null;

  async login(username: string, password: string) {
    const response = await fetch('/api/v1/oauth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'password',
        client_id: 'my-client',
        username,
        password,
      }),
    });

    const data = await response.json();
    this.accessToken = data.access_token;
    this.refreshToken = data.refresh_token;
    this.sessionId = data.session_id;
  }

  async refreshAccessToken() {
    const response = await fetch('/api/v1/oauth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        client_id: 'my-client',
        refresh_token: this.refreshToken!,
      }),
    });

    const data = await response.json();
    this.accessToken = data.access_token;
    this.refreshToken = data.refresh_token;
  }

  async logout(allSessions = false) {
    await fetch('/api/v1/oauth/logout', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ all_sessions: allSessions }),
    });

    this.accessToken = null;
    this.refreshToken = null;
    this.sessionId = null;
  }
}
```

### Python (requests)

```python
import requests

class AuthClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.access_token = None
        self.refresh_token = None
        self.session_id = None

    def login(self, username: str, password: str):
        response = requests.post(
            f"{self.base_url}/api/v1/oauth/token",
            data={
                "grant_type": "password",
                "client_id": "my-client",
                "username": username,
                "password": password,
            },
        )
        response.raise_for_status()
        data = response.json()
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        self.session_id = data["session_id"]

    def refresh_access_token(self):
        response = requests.post(
            f"{self.base_url}/api/v1/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": "my-client",
                "refresh_token": self.refresh_token,
            },
        )
        response.raise_for_status()
        data = response.json()
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]

    def logout(self, all_sessions=False):
        response = requests.post(
            f"{self.base_url}/api/v1/oauth/logout",
            headers={"Authorization": f"Bearer {self.access_token}"},
            json={"all_sessions": all_sessions},
        )
        response.raise_for_status()
        self.access_token = None
        self.refresh_token = None
        self.session_id = None
```

## Ошибки и их обработка

### 400 Bad Request
```json
{
  "error": "invalid_request",
  "error_description": "Missing required parameters: username and password"
}
```

### 401 Unauthorized
```json
{
  "error": "invalid_grant",
  "error_description": "Invalid username or password"
}
```
Или:
```json
{
  "error": "invalid_grant",
  "error_description": "Refresh token has been revoked (reuse detected)"
}
```

### 429 Too Many Requests
```json
{
  "error": "invalid_grant",
  "error_description": "Account temporarily locked. Try again in 15 minutes."
}
```

### 500 Internal Server Error
```json
{
  "error": "server_error",
  "error_description": "An internal error occurred"
}
```

## Миграция БД

Для применения изменений схемы в развёртывании:

```bash
# Применить миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1
```

Новые колонки в `refresh_tokens`:
- `session_id` (VARCHAR, indexed) - уникальный идентификатор сессии
- `last_used` (DATETIME) - последнее использование токена
- `last_rotated_at` (DATETIME) - время последней ротации
- `ip_address` (VARCHAR) - IP адрес клиента
- `user_agent` (VARCHAR) - User-Agent клиента

## FAQ

**Q: Что произойдёт, если я потеряю refresh token?**  
A: Вы сможете получить новый через password grant (logon снова) или использовать другую сессию.

**Q: Как долго может жить сессия?**  
A: Refresh token действителен 30 дней. После этого потребуется повторная аутентификация.

**Q: Может ли один пользователь иметь несколько сессий?**  
A: Да! Каждое устройство получает свой session_id. Вы можете просмотреть и отозвать сессии.

**Q: Что если I обновлю пароль?**  
A: Рекомендуется вызвать `/api/v1/oauth/logout?all_sessions=true` для отзыва всех сессий.

**Q: Почему я получаю "Refresh token reuse detected"?**  
A: Это означает, что кто-то пытается использовать старый токен. Все токены вашей цепи были отозваны. Logon снова и примите меры безопасности.
