# Specification: Role Management API

**Версия:** 1.0.0  
**Дата:** 5 апреля 2026  
**Статус:** Specification  

---

## 1. Overview

Данная спецификация описывает REST API endpoints для управления ролями в CodeLab Auth Service. Все endpoints требуют Bearer token с `admin` scope.

---

## 2. Authentication & Authorization

### 2.1 Requirements

- ✅ Все endpoints требуют Bearer token в заголовке `Authorization: Bearer <token>`
- ✅ Token должен быть valid JWT с RS256 подписью
- ✅ Token должен содержать scope `admin`
- ✅ Если scope отсутствует → 403 Forbidden

### 2.2 Error Responses

```json
{
  "error": "insufficient_scope",
  "error_description": "This endpoint requires 'admin' scope"
}
```

---

## 3. Endpoints

### 3.1 POST /api/v1/admin/roles

**Создать новую роль**

#### Request

```http
POST /api/v1/admin/roles HTTP/1.1
Host: auth.codelab.local
Content-Type: application/json
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
  "name": "content-editor",
  "display_name": "Content Editor",
  "description": "Может редактировать контент и управлять черновиками"
}
```

#### Request Schema

```json
{
  "type": "object",
  "required": ["name"],
  "properties": {
    "name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 255,
      "pattern": "^[a-z0-9-_]+$",
      "description": "Уникальное имя роли (lowercase, hyphen/underscore allowed)"
    },
    "display_name": {
      "type": "string",
      "maxLength": 255,
      "description": "Отображаемое имя (опционально)"
    },
    "description": {
      "type": "string",
      "maxLength": 1000,
      "description": "Описание роли (опционально)"
    }
  }
}
```

#### Response (201 Created)

```http
HTTP/1.1 201 Created
Content-Type: application/json
Location: /api/v1/admin/roles/550e8400-e29b-41d4-a716-446655440000

{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "content-editor",
  "display_name": "Content Editor",
  "description": "Может редактировать контент и управлять черновиками",
  "system_defined": false,
  "created_at": "2026-04-05T12:00:00Z",
  "updated_at": "2026-04-05T12:00:00Z"
}
```

#### Error Responses

**400 Bad Request — невалидные данные**
```json
{
  "error": "invalid_request",
  "error_description": "Role name is required"
}
```

**409 Conflict — роль с таким именем уже существует**
```json
{
  "error": "conflict",
  "error_description": "Role 'content-editor' already exists"
}
```

**403 Forbidden — недостаточно прав**
```json
{
  "error": "insufficient_scope",
  "error_description": "This endpoint requires 'admin' scope"
}
```

#### curl Example

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -d '{
    "name": "content-editor",
    "display_name": "Content Editor",
    "description": "Может редактировать контент"
  }' \
  https://auth.codelab.local/api/v1/admin/roles
```

---

### 3.2 GET /api/v1/admin/roles

**Получить список всех ролей**

#### Request

```http
GET /api/v1/admin/roles HTTP/1.1
Host: auth.codelab.local
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

#### Query Parameters (Optional)

| Parameter | Type | Description |
|-----------|------|-------------|
| `system_defined` | boolean | Фильтр: только встроенные роли (true) или только пользовательские (false) |
| `limit` | integer | Максимум результатов (default: 100, max: 1000) |
| `offset` | integer | Пропустить N результатов (для pagination) |

#### Response (200 OK)

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "roles": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "admin",
      "display_name": "Administrator",
      "description": "Полный доступ ко всем функциям системы",
      "system_defined": true,
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-01T00:00:00Z"
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "user",
      "display_name": "User",
      "description": "Обычный пользователь",
      "system_defined": true,
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 2,
  "limit": 100,
  "offset": 0
}
```

#### curl Example

```bash
# Получить все роли
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  https://auth.codelab.local/api/v1/admin/roles

# Получить только встроенные роли
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  'https://auth.codelab.local/api/v1/admin/roles?system_defined=true'
```

---

### 3.3 GET /api/v1/admin/roles/{role_id}

**Получить конкретную роль по ID**

#### Request

```http
GET /api/v1/admin/roles/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: auth.codelab.local
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

#### Response (200 OK)

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "admin",
  "display_name": "Administrator",
  "description": "Полный доступ ко всем функциям системы",
  "system_defined": true,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

#### Error Responses

**404 Not Found**
```json
{
  "error": "not_found",
  "error_description": "Role '550e8400-...' not found"
}
```

#### curl Example

```bash
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  https://auth.codelab.local/api/v1/admin/roles/550e8400-e29b-41d4-a716-446655440000
```

---

### 3.4 PUT /api/v1/admin/roles/{role_id}

**Обновить роль (display_name и description)**

**Внимание:** Нельзя изменять имя роли (name) — оно immutable!

#### Request

```http
PUT /api/v1/admin/roles/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: auth.codelab.local
Content-Type: application/json
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
  "display_name": "Administrator Updated",
  "description": "Полный доступ (обновленное описание)"
}
```

#### Request Schema

```json
{
  "type": "object",
  "properties": {
    "display_name": {
      "type": "string",
      "maxLength": 255
    },
    "description": {
      "type": "string",
      "maxLength": 1000
    }
  }
}
```

#### Response (200 OK)

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "admin",
  "display_name": "Administrator Updated",
  "description": "Полный доступ (обновленное описание)",
  "system_defined": true,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-04-05T12:00:00Z"
}
```

#### curl Example

```bash
curl -X PUT \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -d '{"display_name": "Administrator Updated"}' \
  https://auth.codelab.local/api/v1/admin/roles/550e8400-e29b-41d4-a716-446655440000
```

---

### 3.5 DELETE /api/v1/admin/roles/{role_id}

**Удалить роль**

**Внимание:** 
- Нельзя удалять встроенные роли (system_defined=true)
- Удаление удалит все user_role_mappings этой роли (CASCADE)

#### Request

```http
DELETE /api/v1/admin/roles/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: auth.codelab.local
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

#### Response (204 No Content)

```http
HTTP/1.1 204 No Content
```

#### Error Responses

**404 Not Found**
```json
{
  "error": "not_found",
  "error_description": "Role '550e8400-...' not found"
}
```

**400 Bad Request — попытка удалить встроенную роль**
```json
{
  "error": "invalid_request",
  "error_description": "Cannot delete system-defined role 'admin'"
}
```

#### curl Example

```bash
curl -X DELETE \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  https://auth.codelab.local/api/v1/admin/roles/550e8400-e29b-41d4-a716-446655440000
```

---

## 4. User Role Endpoints

### 4.1 POST /api/v1/admin/users/{user_id}/roles

**Добавить роль пользователю**

#### Request

```http
POST /api/v1/admin/users/770e8400-e29b-41d4-a716-446655440002/roles HTTP/1.1
Host: auth.codelab.local
Content-Type: application/json
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
  "role_name": "moderator"
}
```

#### Request Schema

```json
{
  "type": "object",
  "required": ["role_name"],
  "properties": {
    "role_name": {
      "type": "string",
      "description": "Имя роли (admin, moderator, user, etc.)"
    }
  }
}
```

#### Response (201 Created)

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "user_id": "770e8400-e29b-41d4-a716-446655440002",
  "role_name": "moderator",
  "created_at": "2026-04-05T12:00:00Z"
}
```

#### Error Responses

**404 Not Found — пользователь или роль не существуют**
```json
{
  "error": "not_found",
  "error_description": "User '770e8400-...' not found"
}
```

**409 Conflict — пользователь уже имеет эту роль**
```json
{
  "error": "conflict",
  "error_description": "User '770e8400-...' already has role 'moderator'"
}
```

#### curl Example

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -d '{"role_name": "moderator"}' \
  https://auth.codelab.local/api/v1/admin/users/770e8400-e29b-41d4-a716-446655440002/roles
```

---

### 4.2 GET /api/v1/admin/users/{user_id}/roles

**Получить список ролей пользователя**

#### Request

```http
GET /api/v1/admin/users/770e8400-e29b-41d4-a716-446655440002/roles HTTP/1.1
Host: auth.codelab.local
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

#### Response (200 OK)

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "user_id": "770e8400-e29b-41d4-a716-446655440002",
  "roles": [
    {
      "name": "user",
      "display_name": "User",
      "description": "Обычный пользователь",
      "system_defined": true
    },
    {
      "name": "moderator",
      "display_name": "Moderator",
      "description": "Модератор контента",
      "system_defined": true
    }
  ]
}
```

#### curl Example

```bash
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  https://auth.codelab.local/api/v1/admin/users/770e8400-e29b-41d4-a716-446655440002/roles
```

---

### 4.3 DELETE /api/v1/admin/users/{user_id}/roles/{role_name}

**Удалить роль пользователя**

#### Request

```http
DELETE /api/v1/admin/users/770e8400-e29b-41d4-a716-446655440002/roles/moderator HTTP/1.1
Host: auth.codelab.local
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

#### Response (204 No Content)

```http
HTTP/1.1 204 No Content
```

#### Error Responses

**404 Not Found**
```json
{
  "error": "not_found",
  "error_description": "User '770e8400-...' does not have role 'moderator'"
}
```

#### curl Example

```bash
curl -X DELETE \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  https://auth.codelab.local/api/v1/admin/users/770e8400-e29b-41d4-a716-446655440002/roles/moderator
```

---

## 5. Error Handling

### 5.1 Standard Error Response Format

Все errors возвращаются в формате OAuth2:

```json
{
  "error": "error_code",
  "error_description": "Human-readable description"
}
```

### 5.2 HTTP Status Codes

| Status | Error Code | Description |
|--------|-----------|-------------|
| 200 | N/A | OK (successful GET) |
| 201 | N/A | Created (successful POST) |
| 204 | N/A | No Content (successful DELETE) |
| 400 | invalid_request | Невалидные параметры или данные |
| 401 | invalid_token | Bearer token невалиден или отсутствует |
| 403 | insufficient_scope | Требуется admin scope |
| 404 | not_found | Ресурс не найден |
| 409 | conflict | Конфликт (дублирование, уже существует) |
| 500 | server_error | Внутренняя ошибка сервера |

---

## 6. Rate Limiting

### 6.1 Limits

- **POST /api/v1/admin/roles** — 10 requests/minute per user
- **POST /api/v1/admin/users/{user_id}/roles** — 100 requests/minute per user
- **DELETE endpoints** — 50 requests/minute per user
- **GET endpoints** — 1000 requests/minute per user

### 6.2 Rate Limit Headers

```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 5
X-RateLimit-Reset: 1712390400
```

### 6.3 Rate Limit Exceeded (429)

```json
{
  "error": "rate_limit_exceeded",
  "error_description": "Too many requests. Try again in 60 seconds."
}
```

---

## 7. Logging

### 7.1 Audit Log Fields

Все операции должны быть залогированы:

```python
{
  "timestamp": "2026-04-05T12:00:00Z",
  "action": "role_created",
  "admin_id": "550e8400-e29b-41d4-a716-446655440000",
  "role_name": "content-editor",
  "status": "success"
}
```

### 7.2 Log Levels

- **INFO** — успешные операции
- **WARN** — попытки неавторизованного доступа
- **ERROR** — ошибки БД, внутренние ошибки

---

## 8. Acceptance Criteria

- [x] Все 8 endpoints реализованы
- [x] Все endpoints требуют admin scope
- [x] Response schemas соответствуют спецификации
- [x] Error handling правильный
- [x] Rate limiting реализован
- [x] Audit logging реализован
- [x] OpenAPI/Swagger документирован
- [x] curl examples работают
- [x] API тесты проходят
- [x] Performance < 200ms для любого endpoint

---

## References

- OAuth2 Error Codes: https://tools.ietf.org/html/rfc6749#section-4.1.2.1
- HTTP Status Codes: https://httpwg.org/specs/rfc9110.html#status.codes
- OpenAPI Specification: https://spec.openapis.org/oas/v3.0.3
