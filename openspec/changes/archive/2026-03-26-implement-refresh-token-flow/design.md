# Дизайн: Полноценная реализация Refresh Token Flow

## Обзор архитектуры

```
┌──────────────────────────────────────────────────────────────────┐
│                  OAuth Token Endpoint                            │
│                 POST /api/v1/oauth/token                         │
└──────────────┬─────────────────────────────────────────────────┘
               │
        ┌──────┴──────────┐
        │                 │
   ┌────▼────┐     ┌──────▼──────────┐
   │ Пароль  │     │ Refresh Token    │
   │ Grant   │     │ Grant            │
   └────┬────┘     └──────┬───────────┘
        │                 │
        └────┬────────────┘
             │
    ┌────────▼────────────────┐
    │ Token Service:          │
    │ - Генерирует токены     │
    │ - Валидирует JWT        │
    └────────┬────────────────┘
             │
    ┌────────▼──────────────────────────┐
    │ RefreshTokenService:              │
    │ - Сохранение refresh token        │
    │ - Валидация токена в БД           │
    │ - Детектирование переиспользования│
    │ - Ротация токенов                 │
    │ - Отзыв цепи токенов              │
    └────────┬──────────────────────────┘
             │
    ┌────────▼──────────────────────────┐
    │ База данных (refresh_tokens)      │
    │ ├── id                            │
    │ ├── jti_hash                      │
    │ ├── user_id                       │
    │ ├── client_id                     │
    │ ├── session_id (НОВОЕ)            │
    │ ├── scope                         │
    │ ├── expires_at                    │
    │ ├── revoked                       │
    │ ├── revoked_at                    │
    │ ├── parent_jti_hash               │
    │ ├── last_rotated_at (НОВОЕ)       │
    │ └── created_at                    │
    └───────────────────────────────────┘

Управление сессиями:
┌──────────────────────────────────────────┐
│ Авторизованный пользователь              │
│ GET /api/v1/oauth/sessions               │
└──────────────┬───────────────────────────┘
               │
       ┌───────▼──────────┐
       │ Список сессий    │
       │ - session_id     │
       │ - created_at     │
       │ - client_id      │
       │ - last_used      │
       └────────────────┘

Отзыв токенов:
┌──────────────────────────────────────────┐
│ POST /api/v1/oauth/logout (Выход)        │
│ DELETE /api/v1/oauth/sessions/{id}       │
└──────────────┬───────────────────────────┘
               │
    ┌──────────▼──────────────┐
    │ Отзыв токена(ов)        │
    │ Mark revoked=True       │
    │ Set revoked_at          │
    └──────────┬──────────────┘
               │
    ┌──────────▼────────────────────────┐
    │ Опционально: Отзыв цепи токенов   │
    │ (если обнаружено переиспользование)│
    └────────────────────────────────────┘
```

## Стратегия ротации токенов

### Текущая реализация
```
1. Пользователь аутентифицируется по паролю
   → Access Token (короткоживущий, 15 мин)
   → Refresh Token (долгоживущий, 30 дней)
   
2. Access Token истекает
   → Клиент отправляет refresh_token на /token endpoint
   → Валидация подписи JWT и claims
   → Проверка БД: валиден ли токен (не отозван, не истекает)?
   → Если валиден: Выдаёт новые токены
     - Новый Access Token
     - Новый Refresh Token (ротирован)
   → Отзов старого Refresh Token
   → Сохранение нового токена со ссылкой parent_jti_hash
```

### Отслеживание цепи ротации
```
Вход пользователя (Начало цепи)
  │
  └─ RT1 (jti_hash=abc123)
       └─ RT2 (parent_jti_hash=abc123) ← ротирован из RT1
            └─ RT3 (parent_jti_hash=rt2_hash) ← ротирован из RT2
                 └─ Если RT2 использован снова → ОБНАРУЖЕНО ПЕРЕИСПОЛЬЗОВАНИЕ!
                      └─ Отзов всей цепи: RT1, RT2, RT3
```

## Детектирование переиспользования токенов

**Сценарий: Атакующий получил старый refresh token**

```
Легитимный поток:
Устройство A: RT1 → (использование) → RT2 ✓ (в БД, RT1 отозван)
Устройство A: RT2 → (использование) → RT3 ✓ (в БД, RT2 отозван)

Атака:
Атакующий имеет RT2 (перехвачен)
Атакующий: RT2 → (попытка использования) → ОШИБКА! (RT2 отозван в БД)
           → SECURITY ALERT: Обнаружено переиспользование токена
           → Отзов всей цепи: RT1, RT2, RT3
           → Пользователь должен заново аутентифицироваться
```

## Управление сессиями

Каждая пара токенов (access + refresh) принадлежит **сессии**, идентифицируемой `session_id`:

```
Пользователь: john@example.com

Сессия 1 (Chrome на Desktop)
├── client_id: web_app_frontend
├── session_id: sess_desktop_abc123
├── created_at: 2026-03-25 08:00:00
├── last_used: 2026-03-25 14:00:00
└── status: активна

Сессия 2 (iOS App)
├── client_id: ios_mobile_app
├── session_id: sess_mobile_xyz789
├── created_at: 2026-03-25 10:00:00
├── last_used: 2026-03-25 13:50:00
└── status: активна

Сессия 3 (Старое Android приложение - следует отозвать)
├── client_id: android_mobile_app
├── session_id: sess_android_old456
├── created_at: 2026-02-01 12:00:00
├── status: отозвана
└── revoked_at: 2026-03-20 09:00:00
```

Пользователь может просмотреть все сессии и отозвать подозрительные.

## Детали реализации

### Расширенная модель RefreshToken
```python
class RefreshToken:
    id: str                         # UUID
    jti_hash: str                   # Уникальный hash JWT ID
    user_id: str                    # FK на users
    client_id: str                  # FK на oauth_clients
    session_id: str                 # НОВОЕ: идентификатор сессии
    scope: str                      # Скопы разделённые пробелом
    expires_at: datetime            # Истечение токена
    revoked: bool                   # Флаг отзыва
    revoked_at: datetime | None
    parent_jti_hash: str | None     # Для цепи ротации
    last_rotated_at: datetime | None  # НОВОЕ: Время последней ротации
    created_at: datetime
```

### Ключевые сервисы и методы

**RefreshTokenService расширения:**
```
- save_refresh_token(db, payload, parent_jti, session_id)
- validate_refresh_token(db, jti) → (is_valid, error_msg)
- revoke_token(db, jti)
- revoke_token_chain(db, token)
- revoke_session(db, user_id, session_id)
- get_user_sessions(db, user_id) → [sessions]
- cleanup_expired_tokens(db, days_to_keep)
```

**Новый SessionService:**
```
- list_sessions(db, user_id) → [session_dto]
- get_session(db, user_id, session_id) → session_dto | None
- revoke_session(db, user_id, session_id) → bool
- get_session_id_from_token(db, jti) → session_id | None
```

### API Endpoints

#### 1. Endpoint выхода (logout)
```
POST /api/v1/oauth/logout
Headers:
  Authorization: Bearer <access_token>
  X-Refresh-Token: <refresh_token> (опционально)

Response:
{
  "message": "Успешно вышли из системы"
}

Поведение:
- Отозыв refresh token связанного с текущим access token
- Если передан X-Refresh-Token, отозвать именно его
```

#### 2. Endpoint списка сессий
```
GET /api/v1/oauth/sessions
Headers:
  Authorization: Bearer <access_token>

Response:
{
  "sessions": [
    {
      "session_id": "sess_abc123",
      "client_id": "web_app_frontend",
      "created_at": "2026-03-25T08:00:00Z",
      "last_used": "2026-03-25T14:00:00Z",
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0..."
    }
  ]
}
```

#### 3. Endpoint отзыва сессии
```
DELETE /api/v1/oauth/sessions/{session_id}
Headers:
  Authorization: Bearer <access_token>

Response:
{
  "message": "Сессия успешно отозвана"
}
```

## Обработка ошибок

```
Ошибки валидации токена:
- "refresh_token_not_found" → 401
- "refresh_token_revoked" → 401
- "refresh_token_expired" → 401
- "refresh_token_reuse_detected" → 401 + отзыв цепи
- "invalid_client" → 401
- "invalid_grant" → 401

Ошибки сессии:
- "session_not_found" → 404
- "unauthorized_session" → 403
```

## Соображения безопасности

1. **Детектирование переиспользования**: Реализовано через отслеживание отзыва
2. **Ротация токенов**: Каждое использование refresh token генерирует новую пару
3. **Отслеживание цепи**: parent_jti_hash позволяет идентифицировать точку компрометации
4. **Изоляция сессий**: Разные клиенты получают разные сессии
5. **Хеширование в БД**: Токены хешированы в БД для защиты от прямой компрометации
6. **Истечение**: Оба токена имеют истечение, очистка старых токенов
7. **Отслеживание отзывов**: Все отзывы заштампованы по времени для аудита
