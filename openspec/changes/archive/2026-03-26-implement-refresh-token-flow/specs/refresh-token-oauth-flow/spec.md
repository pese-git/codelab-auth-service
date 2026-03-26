# Спецификация: Полный OAuth 2.0 Refresh Token Grant Flow

**Версия:** 1.0.0  
**Статус:** ✅ Обновленный компонент  
**Дата:** 2026-03-25

---

## 📋 Обзор

Полная реализация OAuth 2.0 refresh token grant механизма с поддержкой:
- Валидации JWT (подпись, сроки действия)
- Проверки в БД (статус токена, истечение)
- Детектирования переиспользования токенов
- Безопасной ротации токенов

## ADDED Requirements

### Requirement: Реализация Refresh Token Grant Flow

Система ДОЛЖНА поддерживать RFC 6749 Section 6 refresh token grant для получения нового access token без повторной аутентификации.

#### Scenario: Успешное обновление токена
- **WHEN** клиент отправляет валидный refresh token на endpoint /api/v1/oauth/token с grant_type=refresh_token
- **THEN** система возвращает новую пару токенов (access_token, refresh_token) с 200 OK

#### Scenario: Детектирование переиспользования
- **WHEN** клиент пытается использовать refresh token дважды
- **THEN** система отозывает всю цепь токенов и возвращает ошибку invalid_grant с 401 Unauthorized

## Требования функционала

### Refresh Token Grant (RFC 6749 Section 6)

Когда access token истекает, клиент может использовать refresh token для получения нового access token без повторной аутентификации.

### Процесс

1. **Валидация JWT**
   - Проверить подпись refresh token используя RSA публичный ключ
   - Проверить стандартные JWT claims: `exp`, `iat`, `nbf`
   - Проверить custom claims: `sub` (user_id), `client_id`, `jti` (token ID), `scope`
   - Выбросить исключение при ошибке валидации

2. **Валидация в БД**
   - Получить refresh token из таблицы `refresh_tokens` по `jti_hash`
   - Проверить что токен не отозван (`revoked == False`)
   - Проверить что токен не истекает (`expires_at > now`)
   - Если найдено, что токен отозван, это признак переиспользования

3. **Детектирование переиспользования**
   - Если токен в БД отозван → это атака
   - Отозвать ВСЮ цепь токенов для этого пользователя/клиента
   - Выбросить ошибку `invalid_grant`
   - Логировать SECURITY событие

4. **Аутентификация**
   - Получить данные пользователя из `sub` claim
   - Получить данные клиента из `client_id` claim
   - Проверить что клиент существует и активен
   - Проверить что пользователь существует и активен
   - Проверить что пользователь не заблокирован

5. **Генерация новых токенов**
   - Создать новый access token (15 минут истечения)
   - Создать новый refresh token (30 дней истечения)
   - Оба с новыми JWT ID (`jti`)

6. **Сохранение и ротация**
   - Отозвать старый refresh token в БД
   - Сохранить новый refresh token в БД
   - Сохранить `parent_jti_hash` (ссылка на предыдущий токен)
   - Обновить `last_rotated_at` поле

7. **Логирование и аудит**
   - Логировать успешное обновление токена
   - Записать в audit_logs: user_id, client_id, ip_address, user_agent

## API Contract

### Endpoint
```
POST /api/v1/oauth/token
Content-Type: application/x-www-form-urlencoded

Parameters:
- grant_type: "refresh_token" (required)
- client_id: client ID (required)
- refresh_token: refresh token string (required)
- scope: requested scopes (optional, должны быть подмножество оригинальных)
```

### Успешный Response (200 OK)
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 900,
  "refresh_token": "eyJhbGciOiJSUzI1NiIs...",
  "scope": "read write"
}
```

### Ошибки (400 Bad Request или 401 Unauthorized)
```json
{
  "error": "invalid_grant",
  "error_description": "Refresh token has been revoked (reuse detected)"
}
```

Коды ошибок:
- `invalid_request`: Отсутствуют обязательные параметры
- `invalid_client`: Клиент не найден или неактивен
- `invalid_grant`: Токен не валиден, истекает, отозван или переиспользован
- `unauthorized_client`: Клиент не авторизован для данного grant type
- `unsupported_grant_type`: Grant type не поддерживается
- `invalid_scope`: Запрошенный scope недоступен

## Безопасность

### Threat Model

1. **Token Reuse (Переиспользование токена)**
   - Если перехвачен old refresh token, атакующий может использовать его для получения новых токенов
   - **Защита**: В DB каждый новый refresh token отзывает старый. Если старый используется повторно - это атака.
   
2. **Token Leakage (Утечка токена)**
   - Refresh tokens хранятся в БД хешированными
   - Access tokens не хранятся (недолгоживущие)
   - **Защита**: Токены в БД не видны при SQL injection в других таблицах

3. **Man-in-the-Middle (MITM)**
   - Токены передаются в открытом виде по HTTP
   - **Защита**: Require HTTPS in production, использование secure, httponly cookies опционально

4. **Scope Escalation**
   - Клиент пытается получить больше скопов через refresh token
   - **Защита**: Не позволять increase скопов, только subset или same

## Тестовые сценарии

1. **Успешная ротация**
   - Пользователь получает access + refresh token
   - Access token истекает
   - Клиент использует refresh token
   - Получает новую пару токенов
   - Старый refresh token больше не работает

2. **Переиспользование токена**
   - Пользователь получает RT1
   - RT1 ротирован в RT2
   - Атакующий пытается использовать RT1
   - Система обнаруживает переиспользование
   - Отзывает RT1, RT2 и всю цепь
   - Пользователь должен заново аутентифицироваться

3. **Истекший токен**
   - Пользователь пытается использовать истекший refresh token
   - Получает ошибку `invalid_grant`

4. **Отозванный токен**
   - Пользователь логаутится (токен отозван)
   - Пытается использовать старый refresh token
   - Получает ошибку `invalid_grant`

5. **Недействительный клиент**
   - Refresh token выдан для client_id=A
   - Попытка использовать с client_id=B
   - Получает ошибку `invalid_client`

## Зависимости

- `TokenService`: Генерирует и валидирует JWT
- `RefreshTokenService`: Управляет refresh tokens в БД
- `AuthService`: Получение данных пользователя и клиента
- `AuditService`: Логирование операций

## Файлы реализации

- `app/api/v1/oauth.py` - функция `_handle_refresh_grant()`
- `app/services/token_service.py` - методы валидации JWT
- `app/services/refresh_token_service.py` - методы сохранения и валидации токенов
- `app/schemas/oauth.py` - TokenRequest, TokenResponse схемы

## Acceptance Criteria

- [ ] Refresh token grant полностью реализован по RFC 6749
- [ ] Валидация JWT подписи и claims
- [ ] Валидация токена в БД (статус, истечение)
- [ ] Детектирование переиспользования токенов
- [ ] Автоматическая ротация токенов
- [ ] Логирование всех операций
- [ ] Обработка всех edge cases и ошибок
- [ ] Unit тесты покрытие > 90%
- [ ] Интеграционные тесты всех сценариев
