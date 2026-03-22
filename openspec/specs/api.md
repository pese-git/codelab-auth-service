# API Спецификация

**Версия:** 1.0.0  
**Статус:** ✅ Production Ready  
**Дата обновления:** 22 марта 2026

---

## 📡 Обзор API

CodeLab Auth Service предоставляет OAuth2-совместимый API для выдачи и управления токенами. Все endpoints возвращают JSON и поддерживают стандартные HTTP статус коды.

**Base URL:** `https://auth.codelab.local/` или `http://auth-service:8003/`

**Версия API:** v1

---

## 🔐 Аутентификация

### Типы аутентификации

| Тип | Использование | Пример |
|-----|--------------|--------|
| **Без аутентификации** | Public endpoints (/.well-known/jwks.json, /health) | N/A |
| **Bearer Token** | Клиент использует access token | `Authorization: Bearer {access_token}` |
| **Form Data** | OAuth token endpoint | Content-Type: `application/x-www-form-urlencoded` |

### OAuth2 Header

```
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 🔌 API Endpoints

### 1. POST /oauth/token

**Назначение:** Выдача access и refresh токенов

**Content-Type:** `application/x-www-form-urlencoded`

#### 1.1 Password Grant

Используется для первичной аутентификации пользователя по логину и пароля.

**Request:**

```http
POST /oauth/token HTTP/1.1
Host: auth.codelab.local
Content-Type: application/x-www-form-urlencoded

grant_type=password&
username=john@example.com&
password=MyPassword123!&
client_id=codelab-flutter-app&
scope=api:read+api:write
```

**Parameters:**

| Параметр | Тип | Обязательно | Описание |
|----------|-----|-----------|---------|
| `grant_type` | string | ✅ | Всегда: `password` |
| `username` | string | ✅ | Email или username пользователя |
| `password` | string | ✅ | Пароль пользователя (plain text) |
| `client_id` | string | ✅ | Идентификатор клиента |
| `scope` | string | ❌ | Запрашиваемые разрешения (space-separated) |

**Success Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjIwMjQtMDEta2V5LTEifQ.eyJpc3MiOiJodHRwczovL2F1dGguY29kZWxhYi5sb2NhbCIsInN1YiI6IjU1MGU4NDAwLWUyOWItNDFkNC1hNzE2LTQ0NjY1NTQ0MDAwMCIsImF1ZCI6ImNvZGVsYWItYXBpIiwiZXhwIjoxNzEwMDAwOTAwLCJpYXQiOjE3MTAwMDAwMDAsIm5iZiI6MTcxMDAwMDAwMCwic2NvcGUiOiJhcGk6cmVhZCBhcGk6d3JpdGUiLCJqdGkiOiJhMWIyYzNkNC1lNWY2LTc4OTAtYWJjZC1lZjEyMzQ1Njc4OTAiLCJ0eXBlIjoiYWNjZXNzIiwiY2xpZW50X2lkIjoiY29kZWxhYi1mbHV0dGVyLWFwcCJ9.SIGNATURE...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjIwMjQtMDEta2V5LTEifQ.eyJpc3MiOiJodHRwczovL2F1dGguY29kZWxhYi5sb2NhbCIsInN1YiI6IjU1MGU4NDAwLWUyOWItNDFkNC1hNzE2LTQ0NjY1NTQ0MDAwMCIsImF1ZCI6ImNvZGVsYWItYXBpIiwiZXhwIjoxNzEyNTkyMDAwLCJpYXQiOjE3MTAwMDAwMDAsImp0aSI6ImIyYzNkNGU1LWY2YTctODkwMS1iY2RlLWYxMjM0NTY3ODkwMSIsInR5cGUiOiJyZWZyZXNoIiwiY2xpZW50X2lkIjoiY29kZWxhYi1mbHV0dGVyLWFwcCIsInNjb3BlIjoiYXBpOnJlYWQgYXBpOndyaXRlIn0.SIGNATURE...",
  "token_type": "bearer",
  "expires_in": 900,
  "scope": "api:read api:write"
}
```

**Response Fields:**

| Поле | Тип | Описание |
|------|-----|---------|
| `access_token` | string | JWT access token (RS256) |
| `refresh_token` | string | JWT refresh token (RS256) |
| `token_type` | string | Всегда: `bearer` |
| `expires_in` | integer | Время жизни access token (секунды, обычно 900) |
| `scope` | string | Выданные разрешения |

**Error Responses:**

```json
// 400 Bad Request — Отсутствует параметр
{
  "error": "invalid_request",
  "error_description": "Missing required parameter: username"
}

// 400 Bad Request — Невалидный grant_type
{
  "error": "unsupported_grant_type",
  "error_description": "Grant type 'invalid' is not supported"
}

// 401 Unauthorized — Неверные учётные данные
{
  "error": "invalid_grant",
  "error_description": "Invalid username or password"
}

// 400 Bad Request — Невалидный scope
{
  "error": "invalid_scope",
  "error_description": "Requested scope 'api:admin' is not allowed for this client"
}

// 429 Too Many Requests — Rate limit
{
  "error": "rate_limit_exceeded",
  "error_description": "Too many requests. Maximum 5 requests per minute"
}

// 400 Bad Request — Account locked
{
  "error": "invalid_grant",
  "error_description": "Authentication failed"
}
```

#### 1.2 Refresh Token Grant

Используется для получения новых токенов с помощью существующего refresh token.

**Request:**

```http
POST /oauth/token HTTP/1.1
Host: auth.codelab.local
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&
refresh_token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...&
client_id=codelab-flutter-app
```

**Parameters:**

| Параметр | Тип | Обязательно | Описание |
|----------|-----|-----------|---------|
| `grant_type` | string | ✅ | Всегда: `refresh_token` |
| `refresh_token` | string | ✅ | Действующий refresh token |
| `client_id` | string | ✅ | Идентификатор клиента |

**Success Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900,
  "scope": "api:read api:write"
}
```

**Note:** Refresh token rotируется — новый refresh token выдаётся, старый автоматически отзывается.

**Error Responses:**

```json
// 401 Unauthorized — Невалидный refresh token
{
  "error": "invalid_grant",
  "error_description": "Refresh token is invalid or expired"
}

// 401 Unauthorized — Отозванный refresh token
{
  "error": "invalid_grant",
  "error_description": "Refresh token has been revoked"
}

// 401 Unauthorized — Обнаружено повторное использование (АТАКА!)
{
  "error": "invalid_grant",
  "error_description": "Refresh token reuse detected"
}

// 400 Bad Request — Неверный client_id
{
  "error": "invalid_client",
  "error_description": "Client not found or inactive"
}
```

---

### 2. GET /.well-known/jwks.json

**Назначение:** Получить публичные RSA ключи для валидации JWT

**Request:**

```http
GET /.well-known/jwks.json HTTP/1.1
Host: auth.codelab.local
```

**Parameters:** Нет

**Success Response (200 OK):**

```json
{
  "keys": [
    {
      "kty": "RSA",
      "use": "sig",
      "kid": "2024-01-key-1",
      "alg": "RS256",
      "n": "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4cbbfAAtVT86zwu1RK7aPFFxuhDR1L6tSoc_BJECPebWKRXjBZCiFV4n3oknjhMstn64tZ_2W-5JsGY4Hc5n9yBXArwl93lqt7_RN5w6Cf0h4QyQ5v-65YGjQR0_FDW2QvzqY368QQMicAtaSqzs8KJZgnYb9c7d0zgdAZHzu6qMQvRL5hajrn1n91CbOpbISD08qNLyrdkt-bFTWhAI4vMQFh6WeZu0fM4lFd2NcRwr3XPksINHaQ-G_xBniIqbw0Ls1jF44-csFCur-kEgU8awapJzKnqDKgw",
      "e": "AQAB"
    }
  ]
}
```

**Fields:**

| Поле | Описание |
|------|---------|
| `kty` | Key type (всегда `RSA`) |
| `use` | Usage (всегда `sig` — signature) |
| `kid` | Key ID (идентификатор ключа) |
| `alg` | Algorithm (всегда `RS256`) |
| `n` | Modulus (часть публичного ключа) |
| `e` | Exponent (часть публичного ключа, всегда `AQAB`) |

**Notes:**
- Кэшируется в Redis на 1 час
- Может содержать несколько ключей (для rotation)
- Используется для валидации JWT в других сервисах (Gateway, Agent Runtime)

**Error Response:**

```json
// 500 Internal Server Error — Ошибка при загрузке ключей
{
  "error": "server_error",
  "error_description": "Unable to retrieve public keys"
}
```

---

### 3. GET /health

**Назначение:** Health check для балансировщика нагрузки и мониторинга

**Request:**

```http
GET /health HTTP/1.1
Host: auth.codelab.local
```

**Success Response (200 OK):**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-03-22T05:40:00.000Z",
  "checks": {
    "database": "connected",
    "redis": "connected"
  }
}
```

**Degraded Response (503 Service Unavailable):**

```json
{
  "status": "degraded",
  "version": "1.0.0",
  "timestamp": "2026-03-22T05:40:00.000Z",
  "checks": {
    "database": "disconnected",
    "redis": "connected"
  }
}
```

---

## 📊 OAuth2 Flows (Sequence Diagrams)

### Password Grant Flow

```mermaid
sequenceDiagram
    participant Client as Mobile App<br/>(Flutter)
    participant Auth as Auth Service<br/>/oauth/token
    participant DB as Database<br/>(users, tokens)
    participant Cache as Redis<br/>(rate limit, cache)

    Client->>Auth: POST /oauth/token<br/>username, password, client_id
    
    Auth->>Cache: Check rate limit (IP, username)
    Cache-->>Auth: OK / Rate limit exceeded
    alt Rate limit exceeded
        Auth-->>Client: 429 Too Many Requests
    end
    
    Auth->>Cache: Check brute force (username)
    Cache-->>Auth: OK / Account locked
    alt Account locked
        Auth-->>Client: 400 Bad Request
    end
    
    Auth->>DB: SELECT * FROM users WHERE username=?
    DB-->>Auth: User record (with password_hash)
    
    Auth->>Auth: Verify password (bcrypt, constant-time)
    alt Invalid password
        Auth->>Cache: Increment failed attempts
        Auth-->>Client: 401 Unauthorized
    end
    
    Auth->>DB: SELECT * FROM oauth_clients WHERE client_id=?
    DB-->>Auth: OAuth client (scopes, lifetime)
    
    Auth->>Auth: Validate scope against client
    alt Invalid scope
        Auth-->>Client: 400 invalid_scope
    end
    
    Auth->>Auth: Create access token (JWT, RS256)
    Auth->>Auth: Create refresh token (JWT, RS256)
    Auth->>DB: INSERT into refresh_tokens (jti_hash, user_id)
    DB-->>Auth: ✓ Saved
    
    Auth->>DB: UPDATE users SET last_login_at=NOW()
    DB-->>Auth: ✓ Updated
    
    Auth->>DB: INSERT into audit_logs (login_success)
    DB-->>Auth: ✓ Logged
    
    Auth->>Cache: Clear failed attempts counter
    Cache-->>Auth: ✓ Cleared
    
    Auth-->>Client: 200 OK<br/>{access_token, refresh_token, expires_in}
```

### Refresh Token Flow

```mermaid
sequenceDiagram
    participant Client as Mobile App<br/>(Flutter)
    participant Auth as Auth Service<br/>/oauth/token
    participant DB as Database<br/>(refresh_tokens)
    participant Cache as Redis<br/>(JWKS, cache)

    Client->>Auth: POST /oauth/token<br/>grant_type=refresh_token, refresh_token, client_id
    
    Auth->>Auth: Parse JWT (no verification yet)
    Auth->>Auth: Extract jti from payload
    
    Auth->>Auth: Verify JWT signature (RS256)
    alt Invalid signature
        Auth-->>Client: 401 Unauthorized
    end
    
    Auth->>Auth: Check token type (must be "refresh")
    alt Wrong type
        Auth-->>Client: 401 Unauthorized
    end
    
    Auth->>Auth: Compute jti_hash = SHA256(jti)
    Auth->>DB: SELECT * FROM refresh_tokens WHERE jti_hash=?
    DB-->>Auth: Refresh token record
    
    Auth->>Auth: Check if revoked
    alt Token revoked
        Auth-->>Client: 401 Unauthorized
    end
    
    Auth->>Auth: Check if expired
    alt Token expired
        Auth-->>Client: 401 Unauthorized
    end
    
    Auth->>Auth: Check for reuse (token already used?)
    alt REUSE DETECTED!
        Auth->>DB: Revoke entire token chain (parent_jti_hash)
        DB-->>Auth: ✓ Revoked
        Auth->>DB: INSERT into audit_logs (security_incident)
        Auth-->>Client: 401 invalid_grant
    end
    
    Auth->>Auth: Create NEW access token (JWT)
    Auth->>Auth: Create NEW refresh token (JWT)
    
    Auth->>DB: INSERT into refresh_tokens (parent_jti_hash=old_jti)
    DB-->>Auth: ✓ Saved new token
    
    Auth->>DB: UPDATE refresh_tokens SET revoked=TRUE (old token)
    DB-->>Auth: ✓ Old token revoked
    
    Auth->>DB: INSERT into audit_logs (token_refresh)
    DB-->>Auth: ✓ Logged
    
    Auth-->>Client: 200 OK<br/>{access_token, refresh_token, expires_in}
```

### JWT Validation Flow (in Gateway/Resource Server)

```mermaid
sequenceDiagram
    participant Client as Mobile App
    participant Gateway as Gateway Service<br/>(JWTAuthMiddleware)
    participant Auth as Auth Service<br/>/.well-known/jwks.json
    participant Cache as Redis<br/>(JWKS cache)

    Client->>Gateway: GET /api/v1/chat<br/>Authorization: Bearer {access_token}

    Gateway->>Gateway: Extract token from header
    alt No token
        Gateway-->>Client: 401 Unauthorized
    end

    Gateway->>Cache: GET jwks:public_keys (cached?)
    alt Cache hit
        Cache-->>Gateway: JWKS (keys)
    else Cache miss
        Gateway->>Auth: GET /.well-known/jwks.json
        Auth-->>Gateway: JWKS {keys}
        Gateway->>Cache: SET jwks:public_keys (TTL=3600)
        Cache-->>Gateway: ✓ Cached
    end

    Gateway->>Gateway: Parse JWT (extract header, get kid)
    Gateway->>Gateway: Find public key by kid in JWKS

    Gateway->>Gateway: Verify signature (RS256, constant-time)
    alt Invalid signature
        Gateway-->>Client: 401 Unauthorized
    end

    Gateway->>Gateway: Check exp (expiration)
    alt Expired
        Gateway-->>Client: 401 Unauthorized
    end

    Gateway->>Gateway: Check aud (audience="codelab-api")
    alt Wrong audience
        Gateway-->>Client: 401 Unauthorized
    end

    Gateway->>Gateway: Check type (must be "access")
    alt Wrong type
        Gateway-->>Client: 401 Unauthorized
    end

    Gateway->>Gateway: Extract user_id and scope
    Gateway->>Gateway: Store in request.state

    Gateway->>Gateway: Call next middleware/endpoint
    Gateway-->>Client: ✓ Authorized, continue
```

---

## 📋 Request/Response Examples

### Example 1: Successful Login (Password Grant)

**cURL:**
```bash
curl -X POST https://auth.codelab.local/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "username=john@example.com" \
  -d "password=MyPassword123!" \
  -d "client_id=codelab-flutter-app" \
  -d "scope=api:read api:write"
```

**Python:**
```python
import requests

response = requests.post(
    "https://auth.codelab.local/oauth/token",
    data={
        "grant_type": "password",
        "username": "john@example.com",
        "password": "MyPassword123!",
        "client_id": "codelab-flutter-app",
        "scope": "api:read api:write"
    }
)

tokens = response.json()
access_token = tokens["access_token"]
refresh_token = tokens["refresh_token"]
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjIwMjQtMDEta2V5LTEifQ.eyJpc3MiOiJodHRwczovL2F1dGguY29kZWxhYi5sb2NhbCIsInN1YiI6IjU1MGU4NDAwLWUyOWItNDFkNC1hNzE2LTQ0NjY1NTQ0MDAwMCIsImF1ZCI6ImNvZGVsYWItYXBpIiwiZXhwIjoxNzEwMDAwOTAwLCJpYXQiOjE3MTAwMDAwMDAsInNjb3BlIjoiYXBpOnJlYWQgYXBpOndyaXRlIiwianRpIjoiYTFiMmMzZDQtZTVmNi03ODkwLWFiY2QtZWYxMjM0NTY3ODkwIiwidHlwZSI6ImFjY2VzcyIsImNsaWVudF9pZCI6ImNvZGVsYWItZmx1dHRlci1hcHAifQ.SIGNATURE",
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjIwMjQtMDEta2V5LTEifQ.eyJpc3MiOiJodHRwczovL2F1dGguY29kZWxhYi5sb2NhbCIsInN1YiI6IjU1MGU4NDAwLWUyOWItNDFkNC1hNzE2LTQ0NjY1NTQ0MDAwMCIsImF1ZCI6ImNvZGVsYWItYXBpIiwiZXhwIjoxNzEyNTkyMDAwLCJpYXQiOjE3MTAwMDAwMDAsImp0aSI6ImIyYzNkNGU1LWY2YTctODkwMS1iY2RlLWYxMjM0NTY3ODkwMSIsInR5cGUiOiJyZWZyZXNoIiwiY2xpZW50X2lkIjoiY29kZWxhYi1mbHV0dGVyLWFwcCIsInNjb3BlIjoiYXBpOnJlYWQgYXBpOndyaXRlIn0.SIGNATURE",
  "token_type": "bearer",
  "expires_in": 900,
  "scope": "api:read api:write"
}
```

### Example 2: Token Refresh

**cURL:**
```bash
curl -X POST https://auth.codelab.local/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d "client_id=codelab-flutter-app"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiI...",
  "refresh_token": "eyJhbGciOiJSUzI1NiI...",
  "token_type": "bearer",
  "expires_in": 900,
  "scope": "api:read api:write"
}
```

### Example 3: Using Access Token

**cURL:**
```bash
curl -X POST https://gateway.codelab.local/api/v1/chat \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiI..." \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'
```

---

## 🔄 HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| **200** | OK | Успешный запрос |
| **400** | Bad Request | Неверные параметры, невалидный scope, итд. |
| **401** | Unauthorized | Неверные учётные данные, невалидный токен |
| **429** | Too Many Requests | Rate limit exceeded |
| **500** | Internal Server Error | Ошибка на сервере |
| **503** | Service Unavailable | БД или Redis недоступны |

---

## 🔗 Headers

### Request Headers

| Header | Значение | Обязательно | Описание |
|--------|----------|-----------|---------|
| `Content-Type` | `application/x-www-form-urlencoded` | ✅ для /oauth/token | Формат параметров |
| `Authorization` | `Bearer {token}` | ❌ | Для protected endpoints |
| `User-Agent` | `string` | ❌ | Логируется в audit logs |

### Response Headers

| Header | Значение | Описание |
|--------|----------|---------|
| `Content-Type` | `application/json` | JSON формат |
| `Cache-Control` | `no-store` | Не кэшировать (для безопасности) |
| `Pragma` | `no-cache` | Дополнительная директива |
| `X-Content-Type-Options` | `nosniff` | Защита от MIME sniffing |
| `X-Frame-Options` | `DENY` | Защита от clickjacking |
| `Strict-Transport-Security` | `max-age=31536000` | HTTPS only |

---

## 📊 OAuth2 Error Codes (RFC 6749)

| Error | Description | HTTP Code |
|-------|-------------|-----------|
| `invalid_request` | Missing or invalid parameter | 400 |
| `invalid_client` | Client authentication failed | 401 |
| `invalid_grant` | Authorization code/credentials invalid | 401 |
| `invalid_scope` | Scope not valid for this client | 400 |
| `unauthorized_client` | Client not authorized for this grant | 400 |
| `unsupported_grant_type` | Grant type not supported | 400 |
| `unsupported_response_type` | Response type not supported | 400 |
| `server_error` | Server error | 500 |
| `temporarily_unavailable` | Server temporarily unavailable | 503 |

---

## 🎯 Rate Limiting

### Limits

| Limit | Value | Header |
|-------|-------|--------|
| **Per IP** | 5 requests/minute | `X-RateLimit-Limit: 5` |
| **Per Username** | 10 requests/hour | `X-RateLimit-Limit: 10` |

### Response Headers

```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 3
X-RateLimit-Reset: 1711000060
```

### Rate Limit Response (429)

```json
{
  "error": "rate_limit_exceeded",
  "error_description": "Too many requests. Maximum 5 requests per minute",
  "retry_after": 45
}
```

---

## 📞 Контакты

**Разработчик:** Sergey Penkovsky  
**Email:** sergey.penkovsky@gmail.com  
**Версия:** 1.0.0  
**Дата:** 2026-03-22
