# Спецификация: Отзыв токенов (Logout)

**Версия:** 1.0.0  
**Статус:** ✅ Новый компонент  
**Дата:** 2026-03-25

---

## 📋 Обзор

Механизм явного отзыва refresh tokens, позволяющий пользователям выходить из системы (logout). При logout все токены сессии отзываются и больше не могут использоваться для получения новых access tokens.

## ADDED Requirements

### Requirement: Logout endpoint

Система ДОЛЖНА предоставлять endpoint для выхода пользователя из системы с отзывом токенов.

#### Scenario: Logout текущей сессии
- **WHEN** аутентифицированный пользователь отправляет POST /api/v1/oauth/logout
- **THEN** система отозывает все refresh токены текущей сессии (revoked=True, revoked_at=now) и возвращает 200 OK с сообщением о успехе

#### Scenario: Logout всех сессий
- **WHEN** пользователь отправляет POST /api/v1/oauth/logout с параметром all_sessions=true
- **THEN** система отозывает все refresh токены всех сессий пользователя и возвращает 200 OK

### Requirement: Детектирование атак переиспользования

Система ДОЛЖНА обнаруживать и предотвращать атаки переиспользования refresh tokens.

#### Scenario: Обнаружение попытки переиспользования
- **WHEN** клиент пытается использовать refresh token после того как он был отозван
- **THEN** система отозывает всю цепь токенов для этого пользователя/клиента и логирует SECURITY событие

## Требования функционала

### Logout Endpoint

Аутентифицированный пользователь может:
1. Выйти из текущей сессии (logout)
2. Выйти из конкретной сессии (если указан session_id)
3. Выйти из всех сессий (если указана опция)

### Процесс отзыва

1. **Аутентификация**
   - Получить access token из Authorization header
   - Валидировать access token (подпись, claims, истечение)
   - Получить user_id, client_id, jti из access token

2. **Определение токена для отзыва**
   - Если передан X-Refresh-Token header - использовать его jti
   - Иначе - отозвать все токены текущей сессии пользователя для данного client_id
   - Опционально: отозвать все сессии пользователя

3. **Отзыв в БД**
   - Установить revoked=True
   - Установить revoked_at=now
   - Обновить запись в БД

4. **Логирование**
   - Логировать logout событие
   - Записать в audit_logs: user_id, client_id, session_id, ip_address, user_agent, reason="user_logout"

## API Endpoints

### 1. Logout Endpoint (Текущая сессия)

```
POST /api/v1/oauth/logout
Authorization: Bearer <access_token>
Content-Type: application/json

Request Body (optional):
{
  "all_sessions": false  // Выход из всех сессий
}

Response (200 OK):
{
  "message": "Успешно вышли из системы",
  "session_id": "sess_abc123"
}
```

### 2. Logout Specific Token

```
POST /api/v1/oauth/logout
Authorization: Bearer <access_token>
X-Refresh-Token: <specific_refresh_token>
Content-Type: application/json

Response (200 OK):
{
  "message": "Токен успешно отозван"
}
```

### 3. Logout All Sessions

```
POST /api/v1/oauth/logout
Authorization: Bearer <access_token>
Content-Type: application/json

Request Body:
{
  "all_sessions": true
}

Response (200 OK):
{
  "message": "Вышли из всех сессий",
  "sessions_revoked": 3
}
```

## Ошибки

```
401 Unauthorized:
- Отсутствует Access Token
- Access Token невалиден или истекает
- Access Token не может быть распарсен

400 Bad Request:
- Невалидный JSON body
- Неизвестный параметр

404 Not Found:
- Refresh Token не найден (если явно указан)
```

## Безопасность

1. **CSRF Protection**
   - Logout должен быть защищён от CSRF атак
   - Использовать POST метод (не GET)
   - Опционально: требовать CSRF token

2. **Session Binding**
   - Refresh token привязан к user_id + client_id
   - Только владелец access token может отозвать свои токены
   - Невозможно отозвать чужие токены

3. **Audit Trail**
   - Все logout операции логируются
   - Логируются IP адреса и User-Agent
   - Возможность восстановить историю для security анализа

## Тестовые сценарии

### Успешный logout
- Пользователь логируется
- Пользователь логаутится
- Refresh token отозван
- Попытка использовать refresh token даёт 401

### Logout конкретного токена
- Пользователь имеет несколько сессий
- Logout одной сессии
- Другие сессии остаются активными

### Logout всех сессий
- Пользователь имеет 3 сессии
- Logout со all_sessions=true
- Все 3 токена отозваны
- Все попытки использования дают 401

### Logout невалидным access token
- Logout с истекшим access token
- Получить 401 Unauthorized

### Logout с невалидным refresh token
- Попытка отозвать несуществующий refresh token
- Получить 404 или 400 Bad Request

## Интеграция

### Зависимости
- `TokenService`: Валидация access token
- `RefreshTokenService`: Отзыв в БД
- `AuditService`: Логирование

### Файлы реализации
- `app/api/v1/oauth.py` - endpoint функция
- `app/schemas/oauth.py` - LogoutRequest/LogoutResponse схемы
- `app/services/refresh_token_service.py` - revoke_token(), revoke_all_sessions()

## Acceptance Criteria

- [ ] Logout endpoint реализован для текущей сессии
- [ ] Logout конкретного refresh token
- [ ] Logout всех сессий пользователя
- [ ] Валидация access token перед logout
- [ ] Отзыв токенов в БД
- [ ] Логирование всех logout операций
- [ ] Возврат понятных ошибок
- [ ] Unit тесты (> 90% покрытие)
- [ ] Интеграционные тесты всех сценариев
