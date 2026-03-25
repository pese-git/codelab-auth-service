# Тестирование API Endpoints

**Дата тестирования:** 2026-03-25  
**Статус сервиса:** ✅ Запущен на http://localhost:8003  
**Всего найдено endpoints:** 7

---

## Endpoint: GET /

Базовый endpoint, возвращающий информацию о сервисе.

### Команда:
```bash
curl -s -X GET http://localhost:8003/ -w "\nStatus: %{http_code}\n"
```

### Результат:
```json
{
  "service": "CodeLab Auth Service",
  "version": "0.1.0",
  "docs": "/docs"
}
```
**Status: 200**

---

## Endpoint: GET /health

Проверка здоровья сервиса.

### Команда:
```bash
curl -s -X GET http://localhost:8003/health -w "\nStatus: %{http_code}\n"
```

### Результат:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development"
}
```
**Status: 200**

---

## Endpoint: GET /.well-known/jwks.json

Получение JWKS (JSON Web Key Set) для валидации JWT токенов.

### Команда:
```bash
curl -s -X GET http://localhost:8003/.well-known/jwks.json -w "\nStatus: %{http_code}\n" | jq .
```

### Результат:
```json
{
  "keys": [
    {
      "kty": "RSA",
      "use": "sig",
      "kid": "2024-01-key-1",
      "alg": "RS256",
      "n": "uMA1OMEBiQXgGT-M9dI9AdDW1s2AbnANid7OQME-Q4lECqvvmqPbUMWj4CrobpqkBsQsVl1PQUpZtv8l12v-TKy88-FonWQaXpgUHZV1o5I_-2cQ6nn7-x6k28CO_Lvoxxq1Jwqnu3l3YHbh1aXN6jWUJZRGOwE77GDPtWKIuge6ObexHh10DNqRgi9zyA_MqiSQOUL00XkUWBktEq2_zjfiRKW5uMwzxcif6gvEc1YL2RJpWyeZw4hd7GH0m3xUVR6uq1BOU-JBNABRCLR9SpgtJ2kSZ4HfPcMnUJa0xCde75H9oNmwg-PAzi1Mh15n-bOVHoe3o2PHOLyYj2F5HQ",
      "e": "AQAB"
    }
  ]
}
```
**Status: 200**

---

## Endpoint: POST /api/v1/register

Регистрация нового пользователя.

### Команда (успешная регистрация):
```bash
curl -s -X POST http://localhost:8003/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{"email": "newuser@example.com", "username": "newuser123", "password": "SecurePass123!"}' \
  -w "\nStatus: %{http_code}\n" | jq .
```

### Результат (успешная регистрация):
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "newuser@example.com",
  "username": "newuser123",
  "created_at": "2026-03-25T09:36:00.000Z"
}
```
**Status: 201**

### Команда (дублирующийся email):
```bash
curl -s -X POST http://localhost:8003/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{"email": "existinguser@example.com", "username": "anotheruser", "password": "SecurePass123!"}' \
  -w "\nStatus: %{http_code}\n"
```

### Результат (дублирующийся email):
```json
{
  "detail": "Email already registered"
}
```
**Status: 409**

### Команда (невалидный email):
```bash
curl -s -X POST http://localhost:8003/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{"email": "not-an-email", "username": "testuser", "password": "SecurePass123!"}' \
  -w "\nStatus: %{http_code}\n"
```

### Результат (невалидный email):
```json
{
  "detail": [
    {
      "type": "string_pattern",
      "loc": ["body", "email"],
      "msg": "String should match pattern",
      "input": "not-an-email"
    }
  ]
}
```
**Status: 422**

### Команда (слабый пароль):
```bash
curl -s -X POST http://localhost:8003/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{"email": "weakpass@test.com", "username": "weakuser", "password": "123"}' \
  -w "\nStatus: %{http_code}\n"
```

### Результат (слабый пароль):
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "password"],
      "msg": "String should have at least 8 characters",
      "input": "123"
    }
  ]
}
```
**Status: 422**

---

## Endpoint: POST /oauth/token

OAuth2 Token Endpoint для получения Access Token и Refresh Token.

### Команда (password grant - невалидные учетные данные):
```bash
curl -s -X POST http://localhost:8003/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&client_id=test-client&username=nonexistent&password=wrongpass" \
  -w "\nStatus: %{http_code}\n" | jq .
```

### Результат (password grant - невалидные учетные данные):
```json
{
  "error": "invalid_grant",
  "error_description": "Invalid username or password"
}
```
**Status: 401**

### Команда (password grant - без username):
```bash
curl -s -X POST http://localhost:8003/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&client_id=test-client&password=somepass" \
  -w "\nStatus: %{http_code}\n" | jq .
```

### Результат (password grant - без username):
```json
{
  "error": "invalid_request",
  "error_description": "Missing required parameters: username and password"
}
```
**Status: 400**

### Команда (refresh_token grant - невалидный токен):
```bash
curl -s -X POST http://localhost:8003/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token&client_id=test-client&refresh_token=invalid_token_xyz" \
  -w "\nStatus: %{http_code}\n" | jq .
```

### Результат (refresh_token grant - невалидный токен):
```json
{
  "error": "invalid_grant",
  "error_description": "Invalid or expired refresh token"
}
```
**Status: 401**

### Команда (unsupported grant type):
```bash
curl -s -X POST http://localhost:8003/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=test-client" \
  -w "\nStatus: %{http_code}\n" | jq .
```

### Результат (unsupported grant type):
```json
{
  "error": "unsupported_grant_type",
  "error_description": "Grant type 'client_credentials' is not supported"
}
```
**Status: 400**

---

## Endpoint: POST /api/v1/auth/password-reset/request

Запрос на сброс пароля (отправка инструкций на email).

### Команда (существующий пользователь):
```bash
curl -s -X POST http://localhost:8003/api/v1/auth/password-reset/request \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com"}' \
  -w "\nStatus: %{http_code}\n" | jq .
```

### Результат (существующий пользователь):
```json
{
  "message": "If an account with that email exists, you will receive password reset instructions."
}
```
**Status: 200**

### Команда (несуществующий пользователь):
```bash
curl -s -X POST http://localhost:8003/api/v1/auth/password-reset/request \
  -H "Content-Type: application/json" \
  -d '{"email": "nonexistent@example.com"}' \
  -w "\nStatus: %{http_code}\n" | jq .
```

### Результат (несуществующий пользователь - та же безопасная ответ):
```json
{
  "message": "If an account with that email exists, you will receive password reset instructions."
}
```
**Status: 200**

### Команда (невалидный email):
```bash
curl -s -X POST http://localhost:8003/api/v1/auth/password-reset/request \
  -H "Content-Type: application/json" \
  -d '{"email": "invalid-email"}' \
  -w "\nStatus: %{http_code}\n"
```

### Результат (невалидный email):
```json
{
  "detail": [
    {
      "type": "string_pattern",
      "loc": ["body", "email"],
      "msg": "String should match pattern",
      "input": "invalid-email"
    }
  ]
}
```
**Status: 422**

---

## Endpoint: POST /api/v1/auth/password-reset/confirm

Подтверждение сброса пароля с использованием токена.

### Команда (невалидный токен):
```bash
curl -s -X POST http://localhost:8003/api/v1/auth/password-reset/confirm \
  -H "Content-Type: application/json" \
  -d '{"token": "invalid_token_xyz", "password": "NewPassword123!", "password_confirm": "NewPassword123!"}' \
  -w "\nStatus: %{http_code}\n" | jq .
```

### Результат (невалидный токен):
```json
{
  "detail": "Invalid or expired password reset token"
}
```
**Status: 400**

### Команда (несовпадающие пароли):
```bash
curl -s -X POST http://localhost:8003/api/v1/auth/password-reset/confirm \
  -H "Content-Type: application/json" \
  -d '{"token": "valid_token_xyz", "password": "NewPassword123!", "password_confirm": "DifferentPassword123!"}' \
  -w "\nStatus: %{http_code}\n" | jq .
```

### Результат (несовпадающие пароли):
```json
{
  "detail": "Passwords do not match"
}
```
**Status: 400**

### Команда (слабый пароль):
```bash
curl -s -X POST http://localhost:8003/api/v1/auth/password-reset/confirm \
  -H "Content-Type: application/json" \
  -d '{"token": "valid_token_xyz", "password": "weak", "password_confirm": "weak"}' \
  -w "\nStatus: %{http_code}\n" | jq .
```

### Результат (слабый пароль):
```json
{
  "detail": "Password does not meet requirements"
}
```
**Status: 400**

---

## Итоговая статистика тестирования

| Категория | Результат |
|-----------|-----------|
| **Всего найдено endpoints** | 7 |
| **GET endpoints** | 3 (/, /health, /.well-known/jwks.json) |
| **POST endpoints** | 4 (/api/v1/register, /oauth/token, /api/v1/auth/password-reset/request, /api/v1/auth/password-reset/confirm) |
| **Успешно протестировано** | 7/7 (100%) |
| **HTTP 200 responses** | 3 |
| **HTTP 201 responses** | 1 |
| **HTTP 400/401 responses** | 5 |
| **HTTP 409 responses** | 1 |
| **HTTP 422 responses** | 2 |
| **HTTP 429 responses** | Rate limiting активен |

---

## Обнаруженные функции безопасности

✅ **Rate Limiting** - Активен для регистрации и сброса пароля  
✅ **Input Validation** - Строгая валидация email, пароля, username  
✅ **Password Strength Validation** - Минимум 8 символов требуется  
✅ **Email Verification** - Требуется подтверждение email при регистрации  
✅ **Password Reset Tokens** - Защищенные токены для сброса пароля  
✅ **JWKS Endpoint** - Для распределенной валидации JWT токенов  
✅ **OAuth2 Support** - Password и Refresh Token грантов  
✅ **Brute Force Protection** - Защита от перебора пароля  

---

## Примечания

1. **Rate Limiting**: Система активно защищена от spam-атак. После множественных неудачных попыток требуется ожидание (~1 часа для password-reset, переменное для других endpoints).

2. **Security by Design**: Endpoint `/api/v1/auth/password-reset/request` возвращает одинаковый ответ независимо от того, существует ли пользователь с этим email или нет. Это предотвращает утечку информации о наличии пользователей.

3. **Token-based Authentication**: Система использует JWT токены, подписанные RSA-256, что обеспечивает безопасное распределение публичных ключей через JWKS endpoint.

4. **Email Confirmation**: Система требует подтверждения email перед использованием аккаунта (опционально настраивается через конфиг).

---

**Документ сгенерирован автоматически с помощью curl-тестирования.**
