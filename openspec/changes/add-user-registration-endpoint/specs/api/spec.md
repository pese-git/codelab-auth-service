# API Спецификация - Delta

**Версия:** 1.0.0  
**Статус:** Modified  
**Дата:** 2026-03-22

---

## MODIFIED Requirements

### Requirement: Новый endpoint регистрации POST /api/v1/register

**Модифицировано:** Расширение API спецификации с добавлением нового публичного endpoint для регистрации пользователей.

Система ДОЛЖНА предоставить новый endpoint `POST /api/v1/register` для самостоятельной регистрации пользователей без аутентификации.

**Request format:**
```json
{
  "email": "user@example.com",
  "username": "john_doe",
  "password": "securePassword123"
}
```

**Success Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "username": "john_doe",
  "created_at": "2026-03-22T08:35:00.000Z"
}
```

**Error Response (409 Conflict):**
```json
{
  "detail": "Email already registered"
}
```

**Error Response (422 Unprocessable Entity):**
```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "Password must be at least 8 characters",
      "type": "value_error"
    }
  ]
}
```

#### Scenario: Публичный доступ без аутентификации
- **WHEN** клиент отправляет POST на /api/v1/register без Authorization header
- **THEN** система принимает запрос и обрабатывает его (endpoint полностью публичный)

#### Scenario: Endpoint находится в API v1
- **WHEN** клиент отправляет запрос на /api/v1/register
- **THEN** система обрабатывает запрос (не требует /api/v2 или другой версии)

#### Scenario: Успешная регистрация возвращает 201 Created
- **WHEN** клиент успешно регистрируется
- **THEN** HTTP статус код 201 Created (не 200 OK)

#### Scenario: Location header в успешном response
- **WHEN** клиент успешно регистрируется
- **THEN** response содержит Location header с URL нового ресурса (например, /api/v1/users/{user_id})

### Requirement: Request schema валидация
Система ДОЛЖНА валидировать request schema согласно User Registration спецификации.

#### Scenario: Обязательные поля в request
- **WHEN** клиент отправляет request без одного из полей (email, username, password)
- **THEN** система возвращает 422 Unprocessable Entity с указанием недостающего поля

#### Scenario: Extra fields в request игнорируются
- **WHEN** клиент отправляет request с дополнительными полями (например, role, is_admin)
- **THEN** система игнорирует дополнительные поля и обрабатывает только известные

#### Scenario: Empty string values валидируются
- **WHEN** клиент отправляет empty string для email или username
- **THEN** система возвращает 422 Unprocessable Entity

### Requirement: Response headers при успешной регистрации
Система ДОЛЖНА возвращать корректные headers при успешной регистрации.

#### Scenario: Content-Type header
- **WHEN** регистрация успешна
- **THEN** response содержит Content-Type: application/json

#### Scenario: Security headers присутствуют
- **WHEN** регистрация успешна или неудачна
- **THEN** response содержит security headers (X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security)

#### Scenario: Cache-Control header
- **WHEN** регистрация успешна или неудачна
- **THEN** response содержит Cache-Control: no-store (чувствительные данные не кэшируются)

### Requirement: Интеграция с существующей инфраструктурой API
Система ДОЛЖНА следовать существующим паттернам и конвенциям API.

#### Scenario: Версионирование endpoint (v1)
- **WHEN** клиент использует /api/v1/register
- **THEN** endpoint находится в v1 namespace согласно REST API версионированию

#### Scenario: Ошибки возвращают JSON
- **WHEN** регистрация неудачна
- **THEN** error response в JSON формате (не HTML, не plain text)

#### Scenario: Успех возвращает JSON
- **WHEN** регистрация успешна
- **THEN** response в JSON формате с user объектом

---

## ADDED Requirements

### Requirement: Маршрутизация endpoint в FastAPI приложении
Система ДОЛЖНА зарегистрировать новый endpoint в FastAPI приложении.

#### Scenario: Endpoint доступен после регистрации маршрута
- **WHEN** клиент отправляет POST запрос на /api/v1/register
- **THEN** система обрабатывает запрос через зарегистрированный роутер

#### Scenario: Endpoint включен в OpenAPI документацию
- **WHEN** клиент открывает /docs (Swagger UI)
- **THEN** endpoint /api/v1/register видимый и документирован в API

#### Scenario: Endpoint доступен в redoc документации
- **WHEN** клиент открывает /redoc (ReDoc документация)
- **THEN** endpoint /api/v1/register видимый в документации

