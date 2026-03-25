# Спецификация: Управление сессиями

## Обзор

API endpoints для управления активными сессиями пользователя. Позволяет:
- Просмотреть все активные сессии
- Получить детали конкретной сессии
- Отозвать конкретную сессию
- Отозвать все сессии кроме текущей

## Требования функционала

### Концепция сессии

Сессия - это пара (access token + refresh token), выданная для конкретного пользователя и клиента.

Идентификатор сессии (`session_id`):
- Уникален для пользователя + клиента
- Генерируется при выдаче первой пары токенов
- Все последующие ротации токенов используют же session_id
- UUID формат: `sess_<random>`

### Информация в сессии

```python
SessionInfo {
    session_id: str              # Уникальный ID сессии
    client_id: str               # Клиент, для которого создана сессия
    client_name: str             # Читаемое имя клиента
    created_at: datetime         # Время создания
    last_used: datetime          # Время последнего использования
    ip_address: str              # IP адрес клиента
    user_agent: str              # User-Agent браузера/приложения
    is_current: bool             # Текущая ли это сессия
    expires_at: datetime         # Когда истекает refresh token
    status: str                  # "active" | "revoked"
}
```

## API Endpoints

### 1. List Sessions (Список сессий)

```
GET /api/v1/oauth/sessions
Authorization: Bearer <access_token>

Response (200 OK):
{
  "sessions": [
    {
      "session_id": "sess_desktop_abc123",
      "client_id": "web_app_frontend",
      "client_name": "Web Application",
      "created_at": "2026-03-25T08:00:00Z",
      "last_used": "2026-03-25T14:20:00Z",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
      "is_current": true,
      "expires_at": "2026-04-24T08:00:00Z",
      "status": "active"
    },
    {
      "session_id": "sess_mobile_xyz789",
      "client_id": "ios_mobile_app",
      "client_name": "iOS Mobile App",
      "created_at": "2026-03-25T10:00:00Z",
      "last_used": "2026-03-25T13:50:00Z",
      "ip_address": "203.0.113.42",
      "user_agent": "MyApp/1.0 (iOS 17.0)",
      "is_current": false,
      "expires_at": "2026-04-24T10:00:00Z",
      "status": "active"
    }
  ]
}
```

### 2. Get Session Details

```
GET /api/v1/oauth/sessions/{session_id}
Authorization: Bearer <access_token>

Response (200 OK):
{
  "session_id": "sess_desktop_abc123",
  "client_id": "web_app_frontend",
  "client_name": "Web Application",
  "created_at": "2026-03-25T08:00:00Z",
  "last_used": "2026-03-25T14:20:00Z",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
  "is_current": true,
  "expires_at": "2026-04-24T08:00:00Z",
  "status": "active"
}

Response (404 Not Found):
{
  "error": "session_not_found"
}
```

### 3. Revoke Session

```
DELETE /api/v1/oauth/sessions/{session_id}
Authorization: Bearer <access_token>

Response (200 OK):
{
  "message": "Сессия успешно отозвана",
  "session_id": "sess_mobile_xyz789"
}

Response (404 Not Found):
{
  "error": "session_not_found"
}

Response (409 Conflict):
{
  "error": "cannot_revoke_current_session",
  "message": "Невозможно отозвать текущую сессию. Используйте logout endpoint."
}
```

### 4. Revoke All Other Sessions

```
DELETE /api/v1/oauth/sessions?except_current=true
Authorization: Bearer <access_token>

Response (200 OK):
{
  "message": "Все остальные сессии отозваны",
  "revoked_count": 2,
  "remaining_sessions": 1
}
```

## Процесс реализации

### Определение "текущей сессии"

Текущая сессия определяется по access token:
1. Распарсить access token
2. Получить `jti` из claims
3. Найти refresh token в БД по jti_hash родителя
4. Получить session_id из этого refresh token
5. Сравнить с session_id параметром

### Получение информации о сессии

1. Получить все refresh tokens для user_id с status != revoked
2. Для каждого токена:
   - Получить client_id
   - Получить client_name из oauth_clients
   - Получить created_at, last_used (из refresh_tokens)
   - Получить ip_address, user_agent из audit_logs (последняя запись)
   - Получить expires_at
   - Определить is_current (см. выше)

### Отзыв сессии

1. Валидировать что сессия принадлежит текущему пользователю
2. Проверить что это не текущая сессия (если DELETE /sessions/{id})
3. Найти все refresh tokens с session_id
4. Отозвать их все (revoked=True, revoked_at=now)
5. Логировать операцию

## Безопасность

1. **Авторизация**
   - Только владелец может видеть свои сессии
   - Невозможно видеть чужие сессии

2. **Protections**
   - Невозможно отозвать текущую сессию через DELETE (используйте logout)
   - Все операции логируются
   - IP адреса и User-Agent видны для security анализа

3. **Rate Limiting**
   - На requests к session endpoints рекомендуется rate limiting
   - Максимум 10 requests в минуту на пользователя

## Зависимости

- `RefreshTokenService`: Получение и отзыв токенов
- `OAuthClientService`: Информация о клиентах
- `AuditService`: История операций
- `TokenService`: Парсинг access token

## Тестовые сценарии

1. **Список сессий**
   - Пользователь видит свои сессии
   - Информация точна
   - Текущая сессия отмечена

2. **Отзыв сессии**
   - Отзов одной сессии
   - Другие остаются активными
   - Refresh token больше не работает

3. **Отзыв всех кроме текущей**
   - 3 сессии становятся 1
   - Текущая сессия остаётся активной

4. **Невозможно отозвать текущую**
   - Попытка отозвать текущую сессию
   - Получить 409 Conflict

5. **Безопасность доступа**
   - Пользователь A не может видеть сессии пользователя B
   - Пользователь A не может отозвать сессию пользователя B

## Файлы реализации

- `app/api/v1/sessions.py` - новый router
- `app/services/session_service.py` - новый сервис
- `app/schemas/session.py` - SessionInfo, ListSessionsResponse
- `app/main.py` - регистрация router

## Acceptance Criteria

- [ ] GET /sessions endpoint возвращает список сессий
- [ ] GET /sessions/{id} endpoint возвращает детали сессии
- [ ] DELETE /sessions/{id} отзывает сессию
- [ ] DELETE /sessions?except_current=true отзывает все кроме текущей
- [ ] Невозможно отозвать текущую сессию (409)
- [ ] Авторизация и проверка владения
- [ ] Информация в ответах точна и полна
- [ ] Unit тесты (> 90% покрытие)
- [ ] Интеграционные тесты
