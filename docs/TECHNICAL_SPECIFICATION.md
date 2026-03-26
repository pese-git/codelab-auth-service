# Техническое задание: Auth Service для CodeLab

**Версия:** 1.0.0
**Дата:** 20 января 2026
**Статус:** ✅ Реализовано

---

## 1. Введение

### 1.1 Цель документа

Настоящее техническое задание описывает требования к разработке **Auth Service** — микросервиса аутентификации и авторизации для платформы CodeLab, реализующего функции **OAuth2 Authorization Server** с поддержкой Password Grant и Refresh Token Grant на первом этапе (MVP).

### 1.2 Контекст проекта

Auth Service интегрируется в существующую микросервисную архитектуру CodeLab:
- **Gateway** (порт 8000) — точка входа для клиентов
- **Agent Runtime** (порт 8001) — AI агенты и бизнес-логика
- **LLM Proxy** (порт 8002) — прокси для LLM провайдеров
- **Auth Service** (порт 8003) — новый сервис аутентификации

### 1.3 Связь с существующей архитектурой

Текущая архитектура использует простую аутентификацию через `X-Internal-Auth` заголовок с единым API ключом. Auth Service заменит этот механизм на полноценную OAuth2 авторизацию с JWT токенами.

---

## 2. Цели и ограничения MVP

### 2.1 Основные цели

- ✅ Централизовать аутентификацию пользователей
- ✅ Реализовать единый механизм авторизации для всех микросервисов
- ✅ Обеспечить безопасную выдачу access/refresh JWT токенов
- ✅ Заложить архитектуру для последующего перехода на Authorization Code Flow
- ✅ Интегрироваться с существующей инфраструктурой CodeLab
- ✅ Поддержать горизонтальное масштабирование

### 2.2 Не цели MVP

- ❌ SSO между внешними системами
- ❌ Интеграция с внешними OAuth-провайдерами (Google, GitHub и т.д.)
- ❌ UI для управления пользователями и клиентами
- ❌ RBAC (Role-Based Access Control) — только scope-based авторизация
- ❌ Multi-factor authentication (MFA)

---

## 3. Архитектура

### 3.1 Роль сервиса

- **Auth Service** — OAuth2 Authorization Server
- **Gateway, Agent Runtime, LLM Proxy** — Resource Servers

### 3.2 Схема взаимодействия

```
┌─────────────┐
│   Client    │
│  (Flutter)  │
└──────┬──────┘
       │ 1. POST /oauth/token (login/password)
       ▼
┌─────────────────┐
│  Auth Service   │◄──── 2. Validate credentials
│   (port 8003)   │
└────────┬────────┘
         │ 3. Return JWT tokens
         ▼
┌─────────────────┐
│     Client      │
└────────┬────────┘
         │ 4. Request with Bearer token
         ▼
┌─────────────────┐
│    Gateway      │
│   (port 8000)   │◄──── 5. Validate JWT via JWKS
└────────┬────────┘
         │ 6. Forward to Resource Server
         ▼
┌─────────────────┐
│ Agent Runtime / │
│   LLM Proxy     │◄──── 7. Validate JWT via JWKS
└─────────────────┘
```

### 3.3 Интеграция с существующими сервисами

#### Gateway
- Добавить middleware для валидации JWT токенов
- Заменить `InternalAuthMiddleware` на `JWTAuthMiddleware`
- Получать публичные ключи из Auth Service (JWKS endpoint)

#### Agent Runtime & LLM Proxy
- Добавить валидацию JWT токенов для защищенных endpoints
- Извлекать `user_id` и `scope` из JWT payload
- Опционально: сохранять внутреннюю аутентификацию для межсервисного взаимодействия

---

## 4. Технологический стек

| Компонент | Требование                     | Обоснование                                    |
| --------- | ------------------------------ | ---------------------------------------------- |
| Язык      | Python 3.12                    | Соответствие существующим сервисам             |
| Framework | FastAPI                        | Используется во всех сервисах CodeLab          |
| Auth      | OAuth2 Password Grant          | Простота для MVP, совместимость с OAuth2       |
| JWT       | RS256 (RSA)                    | Асимметричная криптография для распределенной валидации |
| DB        | PostgreSQL (SQLAlchemy)        | Production-ready, поддержка транзакций         |
| Cache     | Redis                          | Для blacklist токенов и rate limiting          |
| Crypto    | bcrypt, python-jose            | Стандарт для паролей и JWT                     |
| Transport | HTTPS only                     | Безопасность                                   |
| Миграции  | Alembic                        | Управление схемой БД                           |

---

## 5. OAuth2 Grant Types

### 5.1 Обязательные (MVP)

#### Password Grant
- Для аутентификации пользователя по login/password
- Используется Flutter клиентом для первичного входа

#### Refresh Token Grant
- Для обновления access token без повторного ввода пароля
- Refresh token одноразовый (rotation)

### 5.2 Планируемые (Post-MVP)

- `authorization_code` + PKCE — для веб-приложений
- `client_credentials` — для межсервисного взаимодействия

---

## 6. API Контракты

### 6.1 POST /oauth/token

**Назначение:** Выдача и обновление токенов

**Content-Type:** `application/x-www-form-urlencoded`

#### 6.1.1 Password Grant

**Запрос:**
```http
POST /oauth/token HTTP/1.1
Content-Type: application/x-www-form-urlencoded

grant_type=password&
username=user@example.com&
password=secret123&
client_id=codelab-flutter-app&
scope=api:read api:write
```

**Параметры:**
- `grant_type` (required): `password`
- `username` (required): логин пользователя (email или username)
- `password` (required): пароль пользователя
- `client_id` (required): идентификатор клиента
- `scope` (optional): запрашиваемые scope (разделенные пробелом)

**Ответ (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900,
  "scope": "api:read api:write"
}
```

**Ошибки:**
```json
// 400 Bad Request
{
  "error": "invalid_request",
  "error_description": "Missing required parameter: username"
}

// 401 Unauthorized
{
  "error": "invalid_grant",
  "error_description": "Invalid username or password"
}

// 400 Bad Request
{
  "error": "invalid_scope",
  "error_description": "Requested scope is not allowed for this client"
}
```

#### 6.1.2 Refresh Token Grant

**Запрос:**
```http
POST /oauth/token HTTP/1.1
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&
refresh_token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...&
client_id=codelab-flutter-app
```

**Параметры:**
- `grant_type` (required): `refresh_token`
- `refresh_token` (required): действующий refresh token
- `client_id` (required): идентификатор клиента

**Ответ (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900,
  "scope": "api:read api:write"
}
```

**Ошибки:**
```json
// 401 Unauthorized
{
  "error": "invalid_grant",
  "error_description": "Refresh token is invalid or expired"
}

// 401 Unauthorized
{
  "error": "invalid_grant",
  "error_description": "Refresh token has been revoked"
}
```

---

### 6.2 GET /.well-known/jwks.json

**Назначение:** Публикация публичных RSA ключей для проверки JWT

**Ответ (200 OK):**
```json
{
  "keys": [
    {
      "kty": "RSA",
      "use": "sig",
      "kid": "2024-01-key-1",
      "alg": "RS256",
      "n": "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx...",
      "e": "AQAB"
    }
  ]
}
```

**Использование:**
- Resource Servers кэшируют JWKS и обновляют при необходимости
- Поддержка ротации ключей через `kid` (Key ID)

---

### 6.3 POST /oauth/revoke (опционально для MVP)

**Назначение:** Отзыв refresh token

**Запрос:**
```http
POST /oauth/revoke HTTP/1.1
Content-Type: application/x-www-form-urlencoded

token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...&
token_type_hint=refresh_token&
client_id=codelab-flutter-app
```

**Ответ (200 OK):**
```json
{
  "revoked": true
}
```

---

### 6.4 GET /health

**Назначение:** Health check для мониторинга

**Ответ (200 OK):**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "connected",
  "redis": "connected"
}
```

---

## 7. JWT Спецификация

### 7.1 Access Token

**Характеристики:**
- Алгоритм: RS256 (RSA + SHA-256)
- Время жизни: 15 минут (900 секунд)
- Хранение: НЕ хранится в БД (stateless)
- Размер: ~500-800 байт

**Header:**
```json
{
  "alg": "RS256",
  "typ": "JWT",
  "kid": "2024-01-key-1"
}
```

**Payload:**
```json
{
  "iss": "https://auth.codelab.local",
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "aud": "codelab-api",
  "exp": 1710000900,
  "iat": 1710000000,
  "nbf": 1710000000,
  "scope": "api:read api:write",
  "jti": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "type": "access",
  "client_id": "codelab-flutter-app"
}
```

**Поля:**
- `iss` (Issuer): URL Auth Service
- `sub` (Subject): UUID пользователя
- `aud` (Audience): целевая аудитория (Resource Server)
- `exp` (Expiration): время истечения (Unix timestamp)
- `iat` (Issued At): время выдачи
- `nbf` (Not Before): токен не действителен до этого времени
- `scope`: разрешения (разделенные пробелом)
- `jti` (JWT ID): уникальный идентификатор токена
- `type`: тип токена (`access`)
- `client_id`: идентификатор клиента

### 7.2 Refresh Token

**Характеристики:**
- Алгоритм: RS256
- Время жизни: 30 дней (2592000 секунд)
- Хранение: в БД в хэшированном виде
- Одноразовый: после использования выдается новый (rotation)
- Размер: ~500-800 байт

**Payload:**
```json
{
  "iss": "https://auth.codelab.local",
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "aud": "codelab-api",
  "exp": 1712592000,
  "iat": 1710000000,
  "jti": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "type": "refresh",
  "client_id": "codelab-flutter-app",
  "scope": "api:read api:write"
}
```

**Особенности:**
- При использовании старый refresh token отзывается
- В БД хранится SHA-256 хэш `jti`
- Поддержка reuse detection (защита от replay атак)

---

## 8. Модель данных

### 8.1 Таблица: users

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP NULL,
    
    CONSTRAINT users_username_length CHECK (char_length(username) >= 3),
    CONSTRAINT users_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_is_active ON users(is_active);
```

**Поля:**
- `id`: UUID пользователя (используется в JWT `sub`)
- `username`: уникальное имя пользователя
- `email`: email (используется для входа)
- `password_hash`: bcrypt хэш пароля (cost factor 12)
- `is_active`: флаг активности (для блокировки)
- `is_verified`: флаг верификации email
- `created_at`: дата создания
- `updated_at`: дата последнего обновления
- `last_login_at`: дата последнего входа

---

### 8.2 Таблица: oauth_clients

```sql
CREATE TABLE oauth_clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id VARCHAR(255) UNIQUE NOT NULL,
    client_secret_hash VARCHAR(255) NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    is_confidential BOOLEAN DEFAULT FALSE,
    allowed_scopes TEXT NOT NULL,
    allowed_grant_types TEXT NOT NULL,
    access_token_lifetime INTEGER DEFAULT 900,
    refresh_token_lifetime INTEGER DEFAULT 2592000,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT oauth_clients_client_id_length CHECK (char_length(client_id) >= 8)
);

CREATE INDEX idx_oauth_clients_client_id ON oauth_clients(client_id);
CREATE INDEX idx_oauth_clients_is_active ON oauth_clients(is_active);
```

**Поля:**
- `id`: UUID клиента
- `client_id`: публичный идентификатор клиента
- `client_secret_hash`: bcrypt хэш секрета (NULL для public clients)
- `name`: название клиента (например, "CodeLab Flutter App")
- `description`: описание
- `is_confidential`: тип клиента (confidential/public)
- `allowed_scopes`: разрешенные scope (JSON array или space-separated)
- `allowed_grant_types`: разрешенные grant types (JSON array)
- `access_token_lifetime`: время жизни access token (секунды)
- `refresh_token_lifetime`: время жизни refresh token (секунды)
- `is_active`: флаг активности

**Предустановленные клиенты:**
```sql
INSERT INTO oauth_clients (client_id, name, is_confidential, allowed_scopes, allowed_grant_types)
VALUES 
  ('codelab-flutter-app', 'CodeLab Flutter Application', FALSE, 
   'api:read api:write', '["password", "refresh_token"]'),
  ('codelab-internal', 'CodeLab Internal Services', TRUE,
   'api:admin', '["client_credentials"]');
```

---

### 8.3 Таблица: refresh_tokens

```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jti_hash VARCHAR(64) UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_id VARCHAR(255) NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
    scope TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP NULL,
    parent_jti_hash VARCHAR(64) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT refresh_tokens_expires_at_future CHECK (expires_at > created_at)
);

CREATE INDEX idx_refresh_tokens_jti_hash ON refresh_tokens(jti_hash);
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);
CREATE INDEX idx_refresh_tokens_revoked ON refresh_tokens(revoked);
```

**Поля:**
- `id`: UUID записи
- `jti_hash`: SHA-256 хэш `jti` из JWT (для поиска)
- `user_id`: ссылка на пользователя
- `client_id`: ссылка на клиента
- `scope`: разрешения токена
- `expires_at`: время истечения
- `revoked`: флаг отзыва
- `revoked_at`: время отзыва
- `parent_jti_hash`: хэш родительского refresh token (для rotation chain)
- `created_at`: дата создания

**Очистка истекших токенов:**
```sql
-- Периодическая задача (cron)
DELETE FROM refresh_tokens 
WHERE expires_at < NOW() - INTERVAL '7 days';
```

---

### 8.4 Таблица: audit_logs (опционально)

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    client_id VARCHAR(255) NULL,
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB NULL,
    ip_address INET NULL,
    user_agent TEXT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_success ON audit_logs(success);
```

**Event Types:**
- `login_success`
- `login_failed`
- `token_refresh`
- `token_revoke`
- `password_change`
- `user_created`
- `user_blocked`

---

## 9. Безопасность

### 9.1 Обязательные требования

#### Транспорт
- ✅ HTTPS only (TLS 1.2+)
- ✅ HSTS заголовки
- ✅ Secure cookies (если используются)

#### Криптография
- ✅ bcrypt для паролей (cost factor 12)
- ✅ RS256 для JWT (RSA 2048 bit)
- ✅ SHA-256 для хэширования refresh token JTI
- ✅ Криптографически стойкие генераторы случайных чисел

#### Защита от атак
- ✅ Rate limiting на `/oauth/token` (5 попыток / минуту на IP)
- ✅ Rate limiting на `/oauth/token` (10 попыток / час на username)
- ✅ Защита от brute-force (временная блокировка после N неудачных попыток)
- ✅ Защита от timing attacks (constant-time сравнение)
- ✅ CORS настройки (whitelist доменов)
- ✅ SQL injection защита (параметризованные запросы)
- ✅ XSS защита (валидация входных данных)

#### Валидация
- ✅ Строгая валидация всех входных параметров
- ✅ Проверка формата email
- ✅ Требования к паролю (минимум 8 символов, сложность)
- ✅ Проверка allowed_scopes для клиента
- ✅ Проверка grant_type для клиента

### 9.2 Обработка ошибок

**Принципы:**
- ❌ Не раскрывать внутреннюю информацию
- ❌ Не указывать, что именно неверно (username или password)
- ✅ Использовать стандартные OAuth2 error codes
- ✅ Логировать детали ошибок на сервере

**Примеры безопасных сообщений:**
```json
// Вместо: "User not found"
{
  "error": "invalid_grant",
  "error_description": "Invalid username or password"
}

// Вместо: "Password is incorrect"
{
  "error": "invalid_grant",
  "error_description": "Invalid username or password"
}

// Вместо: "Account is locked"
{
  "error": "invalid_grant",
  "error_description": "Authentication failed"
}
```

### 9.3 Refresh Token Security

#### Rotation
- При каждом использовании refresh token выдается новый
- Старый refresh token отзывается
- Цепочка токенов отслеживается через `parent_jti_hash`

#### Reuse Detection
```python
# Если обнаружено повторное использование отозванного refresh token:
# 1. Отозвать всю цепочку токенов пользователя
# 2. Залогировать инцидент безопасности
# 3. Опционально: уведомить пользователя
```

#### Хранение
- В БД хранится только SHA-256 хэш `jti`
- Полный refresh token никогда не хранится в открытом виде

---

## 10. Логирование и аудит

### 10.1 Обязательные события

**Успешные операции:**
- ✅ Успешный вход (login_success)
- ✅ Обновление токена (token_refresh)
- ✅ Отзыв токена (token_revoke)
- ✅ Создание пользователя (user_created)

**Неуспешные операции:**
- ✅ Неудачная попытка входа (login_failed)
- ✅ Использование невалидного refresh token (token_invalid)
- ✅ Обнаружение reuse refresh token (security_incident)
- ✅ Rate limit exceeded (rate_limit_exceeded)

### 10.2 Формат логов

```json
{
  "timestamp": "2024-01-05T10:30:00.000Z",
  "level": "INFO",
  "event_type": "login_success",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "client_id": "codelab-flutter-app",
  "ip_address": "192.168.1.100",
  "user_agent": "CodeLab/1.0.0 (Flutter)",
  "scope": "api:read api:write"
}
```

### 10.3 Что НЕ логировать

- ❌ Пароли (даже хэши)
- ❌ Полные токены (access или refresh)
- ❌ Client secrets
- ❌ Персональные данные (кроме user_id)

---

## 11. Email Notifications (SMTP Integration)

### 11.1 Обзор

Auth Service поддерживает отправку email уведомлений при важных событиях в системе. Функциональность реализована через интеграцию SMTP с поддержкой асинхронной обработки в background.

**Типы уведомлений:**
- Welcome email — при регистрации пользователя
- Email confirmation — верификация email адреса
- Password reset — сброс пароля

### 11.2 SMTP Конфигурация

**Переменные окружения:**

```bash
# SMTP сервер
AUTH_SERVICE__SMTP_HOST=smtp.gmail.com           # Хост SMTP сервера
AUTH_SERVICE__SMTP_PORT=587                      # Порт (обычно 587 для TLS, 465 для SSL)
AUTH_SERVICE__SMTP_USERNAME=your-email@gmail.com # Имя пользователя
AUTH_SERVICE__SMTP_PASSWORD=your-app-password    # Пароль или app-specific password
AUTH_SERVICE__SMTP_FROM_EMAIL=noreply@codelab.com # Email отправителя

# Опции
AUTH_SERVICE__SMTP_USE_TLS=true                  # Использовать STARTTLS (по умолчанию true)
AUTH_SERVICE__SMTP_TIMEOUT=30                    # Timeout соединения в секундах
AUTH_SERVICE__SMTP_MAX_RETRIES=3                 # Максимум попыток отправки

# Управление функциями
AUTH_SERVICE__SEND_WELCOME_EMAIL=true            # Отправлять приветственные письма
AUTH_SERVICE__REQUIRE_EMAIL_CONFIRMATION=true    # Требовать подтверждение email
AUTH_SERVICE__SEND_PASSWORD_RESET_EMAIL=true     # Отправлять письма сброса пароля
```

**Поддерживаемые SMTP провайдеры:**

| Провайдер | Host | Port | TLS | Authentication |
|-----------|------|------|-----|----------------|
| Gmail | smtp.gmail.com | 587 | ✅ | App password |
| SendGrid | smtp.sendgrid.net | 587 | ✅ | API Key as password |
| AWS SES | email-smtp.{region}.amazonaws.com | 587 | ✅ | SMTP credentials |
| Mailgun | smtp.mailgun.org | 587 | ✅ | postmaster@domain |
| MailHog (dev) | mailhog | 1025 | ❌ | None required |

### 11.3 Email API Endpoints

#### POST /api/v1/register

**Обновленное поведение:** При успешной регистрации отправляются email уведомления:

```python
# После создания пользователя:
# 1. Отправка welcome email (асинхронно)
# 2. Если require_email_confirmation=True: отправка confirmation email (асинхронно)
# 3. Ошибки email не влияют на результат регистрации (201 Created)
```

**Ответ:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "email": "john@example.com",
  "created_at": "2026-03-25T06:00:00Z",
  "is_verified": false
}
```

#### GET /api/v1/confirm-email

**Назначение:** Подтверждение email адреса по токену

**Параметры:**
- `token` (query, required): confirmation token из email

**Запрос:**
```http
GET /api/v1/confirm-email?token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Ответ (200 OK):**
```json
{
  "message": "Email confirmed successfully",
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Ошибки:**
```json
// 400 Bad Request - невалидный токен
{
  "error": "invalid_token",
  "error_description": "Confirmation token is invalid or expired"
}

// 400 Bad Request - токен уже использован
{
  "error": "token_already_used",
  "error_description": "This confirmation token has already been used"
}
```

### 11.4 Email Templates

Шаблоны хранятся в `app/templates/emails/` и используют Jinja2 для динамического контента.

**Структура:**

```
app/templates/emails/
├── base.html                    # Базовый layout
├── welcome/
│   ├── template.html            # HTML версия
│   └── subject.txt              # Тема письма
├── confirmation/
│   ├── template.html
│   └── subject.txt
└── password_reset/
    ├── template.html
    └── subject.txt
```

**Переменные в шаблонах:**

| Шаблон | Переменные |
|--------|-----------|
| welcome | `username`, `email`, `activation_link`, `registration_date` |
| confirmation | `username`, `confirmation_link`, `expires_at` |
| password_reset | `username`, `reset_link`, `expires_at` |

**Пример шаблона:**

```html
<!-- app/templates/emails/welcome/template.html -->
{% extends "base.html" %}

{% block content %}
<h1>Welcome to CodeLab, {{ username }}!</h1>
<p>Thank you for registering. Your account is ready to use.</p>
<p>Registered: {{ registration_date|strftime('%Y-%m-%d %H:%M:%S') }}</p>
{% endblock %}
```

### 11.5 Retry Логика

**Exponential Backoff:**

```
Попытка 1: 0 сек (сразу)
Попытка 2: 2 сек (base_delay * 2^1)
Попытка 3: 4 сек (base_delay * 2^2)
```

**Формула:** `delay = base_delay * (2 ^ attempt) ± 10% (jitter)`

**Retryable ошибки:**
- `asyncio.TimeoutError` — timeout соединения
- `ConnectionError` — ошибка соединения
- `SMTPServerError` 4xx — временные ошибки SMTP сервера

**Non-retryable ошибки:**
- `SMTPAuthenticationError` — неправильные credentials
- `SMTPServerError` 5xx — постоянная ошибка сервера

**Пример логирования:**

```json
{
  "timestamp": "2026-03-25T06:00:00.000Z",
  "level": "INFO",
  "event_type": "email_sent",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "template_name": "welcome",
  "recipient": "jo***@example.com",
  "attempt": 1,
  "success": true
}
```

### 11.6 Email Confirmation Tokens

**Таблица: email_confirmation_tokens**

```sql
CREATE TABLE email_confirmation_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT token_expires_future CHECK (expires_at > created_at)
);

CREATE INDEX idx_email_confirmation_tokens_token ON email_confirmation_tokens(token);
CREATE INDEX idx_email_confirmation_tokens_expires_at ON email_confirmation_tokens(expires_at);
```

**Поля:**
- `id`: UUID записи
- `user_id`: ссылка на пользователя (unique — один активный токен на пользователя)
- `token`: хэш токена для поиска (не хранится в открытом виде)
- `expires_at`: время истечения токена (обычно 24 часа)
- `created_at`: дата создания

**Время жизни:** 24 часа (можно настроить через конфиг)

**Одноразовое использование:** Токен удаляется после успешного подтверждения

### 11.7 Security Considerations

**Что НЕ логировать:**
- ❌ Полные email адреса (маскировать: `jo***@example.com`)
- ❌ SMTP credentials (username, password)
- ❌ Confirmation tokens
- ❌ Reset tokens

**TLS/Encryption:**
- ✅ SMTP должен использовать STARTTLS или SSL
- ✅ Email адреса шифруются в transit
- ✅ Credentials хранятся в переменных окружения (не в коде)

**Rate Limiting:**
- Не более 3 попыток отправления на пользователя в минуту
- Не более 5 запросов подтверждения email в час на IP

**Validation:**
- Валидация email формата перед отправкой
- Проверка наличия пользователя перед отправкой confirmation email
- Проверка истечения токена перед подтверждением

### 11.8 Error Handling

**Graceful Degradation:**

```python
try:
    await send_welcome_email(user)
except EmailSendError as e:
    logger.warning(f"Failed to send welcome email: {e}")
    # Регистрация продолжается, несмотря на ошибку email
    pass
```

**Логирование ошибок:**

```json
{
  "timestamp": "2026-03-25T06:00:00.000Z",
  "level": "ERROR",
  "event_type": "email_failed",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "template_name": "confirmation",
  "error": "SMTPServerError",
  "retry_count": 3,
  "final_attempt": true
}
```

---

## 12. Password Reset Функциональность

### 12.1 Обзор

Password Reset — функциональность для безопасного изменения пароля пользователя через email подтверждение. Использует одноразовые токены с ограниченным временем жизни и защиту от брут-форса.

**Основные компоненты:**
- Генерация криптографически стойких токенов (`secrets.token_urlsafe`)
- SHA-256 хеширование токенов при сохранении в БД
- Асинхронная отправка email с ссылкой сброса
- Rate limiting на запросы и подтверждения
- Одноразовое использование токена

### 12.2 API Endpoints

#### POST /api/v1/auth/password-reset/request

**Назначение:** Запрос на сброс пароля (отправка инструкций на email)

**Запрос:**
```http
POST /api/v1/auth/password-reset/request HTTP/1.1
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Параметры:**
- `email` (required): Email адрес пользователя

**Ответ (200 OK):**
```json
{
  "message": "If an account with that email exists, you will receive password reset instructions."
}
```

**Ответ всегда 200 OK** (безопасность: не раскрываем наличие пользователя)

**Ошибки:**
```json
// 400 Bad Request - невалидный email
{
  "detail": "Invalid email format"
}

// 429 Too Many Requests - превышен лимит (3 запроса/час на email)
{
  "detail": "Too many password reset requests. Please try again later."
}
```

**Rate Limiting:**
- 3 запроса за 1 час на email адрес
- 5 запросов за 1 час на IP адрес (защита от распределенных атак)

#### POST /api/v1/auth/password-reset/confirm

**Назначение:** Подтверждение сброса пароля с использованием токена

**Запрос:**
```http
POST /api/v1/auth/password-reset/confirm HTTP/1.1
Content-Type: application/json

{
  "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "password": "NewPassword123!",
  "password_confirm": "NewPassword123!"
}
```

**Параметры:**
- `token` (required): Токен из email ссылки
- `password` (required): Новый пароль
- `password_confirm` (required): Подтверждение пароля

**Ответ (200 OK):**
```json
{
  "message": "Password changed successfully"
}
```

**Ошибки:**
```json
// 400 Bad Request - невалидный/истекший токен
{
  "detail": "Invalid or expired password reset token"
}

// 400 Bad Request - пароли не совпадают
{
  "detail": "Passwords do not match"
}

// 400 Bad Request - пароль не соответствует требованиям
{
  "detail": "Password does not meet requirements: minimum 8 characters, at least one uppercase, one digit and one special character"
}

// 429 Too Many Requests - превышен лимит попыток (10 за 5 минут на IP)
{
  "detail": "Too many password reset attempts. Please try again later."
}
```

**Rate Limiting:**
- 10 попыток за 5 минут на IP адрес
- При превышении: IP блокируется на 15 минут

### 12.3 Token Generation

**Генерация токенов:**

```python
# Генерация
token = secrets.token_urlsafe(32)  # ~43 символа, URL-safe

# Хеширование для сохранения в БД
import hashlib
token_hash = hashlib.sha256(token.encode()).hexdigest()

# Сохранение в БД: token_hash
# Отправка пользователю: token (в открытом виде через email)
```

**Параметры токена:**
- Длина: 32 байта (~43 символа в base64url)
- Алгоритм: SHA-256 для хеширования
- Время жизни: 30 минут
- Одноразовое использование: да

**Безопасность:**
- Криптографически стойкий генератор (`secrets` модуль)
- Constant-time сравнение при верификации
- В БД хранится только хэш, полный токен не сохраняется

### 12.4 Таблица: password_reset_tokens

```sql
CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP NULL,
    
    CONSTRAINT token_expires_future CHECK (expires_at > created_at),
    CONSTRAINT used_after_created CHECK (used_at IS NULL OR used_at >= created_at)
);

CREATE INDEX idx_password_reset_tokens_token_hash ON password_reset_tokens(token_hash);
CREATE INDEX idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);
CREATE INDEX idx_password_reset_tokens_expires_at ON password_reset_tokens(expires_at);
```

**Поля:**
- `id`: UUID записи
- `user_id`: ссылка на пользователя (UNIQUE — один активный токен на пользователя)
- `token_hash`: SHA-256 хэш токена для поиска (не хранится полный токен)
- `created_at`: время создания
- `expires_at`: время истечения (обычно created_at + 30 минут)
- `used_at`: время использования (NULL если не использован)

### 12.5 Flow Сброса Пароля

```
1. Пользователь запрашивает сброс пароля
   POST /api/v1/auth/password-reset/request
   {
     "email": "user@example.com"
   }
   ↓
2. Система проверяет лимиты (rate limiting)
   - 3 запроса/час на email
   - 5 запросов/час на IP
   ↓
3. Система ищет пользователя по email
   - Если не найден: всё равно возвращает 200 OK
   ↓
4. Генерируется токен и сохраняется в БД
   - token = secrets.token_urlsafe(32)
   - token_hash = SHA256(token)
   - Время жизни: 30 минут
   - Одноразовое использование
   ↓
5. Отправляется email с ссылкой
   - Ссылка: /reset-password?token={token}
   - Асинхронная отправка (background task)
   - Отправка может повторяться с retry logic
   ↓
6. Пользователь переходит по ссылке и вводит новый пароль
   POST /api/v1/auth/password-reset/confirm
   {
     "token": "...",
     "password": "NewPassword123!",
     "password_confirm": "NewPassword123!"
   }
   ↓
7. Система проверяет лимиты (10 попыток/5 минут на IP)
   ↓
8. Система верифицирует токен
   - Существует ли в БД
   - Не истек ли (expires_at > NOW)
   - Не использован ли (used_at IS NULL)
   ↓
9. Система валидирует пароль
   - Минимум 8 символов
   - Заглавная буква
   - Цифра
   - Специальный символ
   ↓
10. Пароли совпадают?
    ↓
11. Обновление пароля пользователя
    - Хеширование bcrypt (cost 12)
    - Обновление password_hash
    - Обновление updated_at
    ↓
12. Токен помечается как использованный
    - used_at = NOW()
    ↓
13. Логирование события (audit trail)
    ↓
14. Возврат 200 OK
```

### 12.6 Security Features

**Защита от основных атак:**

1. **Brute-force атаки на подтверждение:**
   - Лимит: 10 попыток за 5 минут на IP
   - Блокировка на 15 минут при превышении
   - Логирование всех попыток

2. **Spam-атаки на запросы сброса:**
   - Лимит: 3 запроса/час на email
   - Лимит: 5 запросов/час на IP
   - Возврат одинакового ответа независимо от наличия пользователя

3. **Реиспользование токена:**
   - Токен помечается как использованный (used_at)
   - При повторной попытке: "Invalid or expired token"
   - Логирование попытки реиспользования

4. **Кража токена:**
   - Транспорт: HTTPS only
   - Email рассылка через SMTP с TLS
   - В логах токены не сохраняются

5. **Timing attacks:**
   - Constant-time сравнение хешей
   - Использование `hmac.compare_digest()`

### 12.7 Логирование

**События для логирования:**

```json
// Успешный запрос сброса пароля
{
  "timestamp": "2026-03-25T10:30:00.000Z",
  "level": "INFO",
  "event_type": "password_reset_requested",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "us***@example.com",
  "ip_address": "192.168.1.100",
  "success": true
}

// Успешное подтверждение сброса пароля
{
  "timestamp": "2026-03-25T10:35:00.000Z",
  "level": "INFO",
  "event_type": "password_reset_confirmed",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "ip_address": "192.168.1.100",
  "success": true
}

// Превышение лимита (rate limit)
{
  "timestamp": "2026-03-25T10:40:00.000Z",
  "level": "WARNING",
  "event_type": "password_reset_rate_limit_exceeded",
  "email": "us***@example.com",
  "ip_address": "192.168.1.100",
  "limit_type": "per_email",
  "limit": "3/hour"
}

// Невалидный токен при подтверждении
{
  "timestamp": "2026-03-25T10:45:00.000Z",
  "level": "WARNING",
  "event_type": "password_reset_invalid_token",
  "ip_address": "192.168.1.100",
  "reason": "expired"
}

// Brute-force обнаружение
{
  "timestamp": "2026-03-25T10:50:00.000Z",
  "level": "CRITICAL",
  "event_type": "password_reset_brute_force_detected",
  "ip_address": "192.168.1.100",
  "failed_attempts": 10,
  "blocked_until": "2026-03-25T11:05:00.000Z"
}
```

**Что НЕ логировать:**
- ❌ Полные токены
- ❌ Новые пароли
- ❌ Старые пароли
- ❌ Полные email адреса (маскировать: us***@example.com)

---

## 12. Производительность и масштабирование

### 11.1 Требования к производительности

- ⚡ Время ответа `/oauth/token` < 200 мс (p95)
- ⚡ Время ответа `/.well-known/jwks.json` < 50 мс (p95)
- ⚡ Throughput: 100 RPS на инстанс
- ⚡ Доступность: 99.9% (SLA)

### 11.2 Горизонтальное масштабирование

**Stateless дизайн:**
- Access tokens не хранятся в БД
- Нет in-memory сессий
- Все состояние в PostgreSQL и Redis

**Кэширование:**
- JWKS кэшируется в Redis (TTL 1 час)
- OAuth clients кэшируются в Redis (TTL 5 минут)
- User lookups кэшируются (TTL 1 минута)

**Database:**
- Connection pooling (SQLAlchemy)
- Read replicas для аудит логов
- Индексы на часто используемые поля

### 11.3 Redis использование

```python
# Rate limiting
key = f"rate_limit:ip:{ip_address}"
redis.incr(key, expire=60)

# Refresh token blacklist (для быстрой проверки)
key = f"revoked_token:{jti_hash}"
redis.setex(key, ttl=refresh_token_lifetime, value="1")

# JWKS cache
key = "jwks:public_keys"
redis.setex(key, ttl=3600, value=json.dumps(jwks))
```

---

## 12. Интеграция с существующими сервисами

### 12.1 Gateway

**Изменения:**

1. Добавить зависимость `python-jose[cryptography]`
2. Создать `JWTAuthMiddleware`:

```python
# gateway/app/middleware/jwt_auth.py
from jose import jwt, JWTError
import httpx

class JWTAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, jwks_url: str):
        super().__init__(app)
        self.jwks_url = jwks_url
        self.jwks_cache = None
        self.jwks_cache_time = 0
    
    async def get_jwks(self):
        # Кэширование JWKS на 1 час
        if time.time() - self.jwks_cache_time > 3600:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_url)
                self.jwks_cache = response.json()
                self.jwks_cache_time = time.time()
        return self.jwks_cache
    
    async def dispatch(self, request: Request, call_next):
        # Публичные endpoints
        if request.url.path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Извлечь токен
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"error": "unauthorized"})
        
        token = auth_header[7:]
        
        # Валидировать JWT
        try:
            jwks = await self.get_jwks()
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                audience="codelab-api"
            )
            
            # Добавить user_id в request state
            request.state.user_id = payload["sub"]
            request.state.scope = payload["scope"]
            
        except JWTError as e:
            return JSONResponse(status_code=401, content={"error": "invalid_token"})
        
        return await call_next(request)
```

3. Обновить `main.py`:

```python
from app.middleware.jwt_auth import JWTAuthMiddleware

app.add_middleware(
    JWTAuthMiddleware,
    jwks_url="http://auth-service:8003/.well-known/jwks.json"
)
```

### 12.2 Agent Runtime

**Изменения:**

1. Добавить аналогичный `JWTAuthMiddleware`
2. Использовать `request.state.user_id` для привязки сессий к пользователям
3. Обновить модели для хранения `user_id`

### 12.3 Docker Compose

**Добавить сервис:**

```yaml
auth-service:
  build:
    context: ./auth-service
    dockerfile: Dockerfile
  ports:
    - "${AUTH_SERVICE_PORT}:${AUTH_SERVICE_PORT}"
  environment:
    - ENVIRONMENT=${ENVIRONMENT}
    - PORT=${AUTH_SERVICE_PORT}
    - AUTH_SERVICE__DB_URL=postgresql://postgres:postgres@postgres:5432/auth_db
    - AUTH_SERVICE__REDIS_URL=redis://redis:6379/0
    - AUTH_SERVICE__LOG_LEVEL=${AUTH_SERVICE__LOG_LEVEL}
    - AUTH_SERVICE__JWT_ISSUER=https://auth.codelab.local
    - AUTH_SERVICE__JWT_AUDIENCE=codelab-api
    - AUTH_SERVICE__ACCESS_TOKEN_LIFETIME=900
    - AUTH_SERVICE__REFRESH_TOKEN_LIFETIME=2592000
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
  networks:
    - codelab-network
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:${AUTH_SERVICE_PORT}/health"]
    interval: 30s
    timeout: 10s
    retries: 3

postgres:
  image: postgres:16-alpine
  environment:
    - POSTGRES_USER=postgres
    - POSTGRES_PASSWORD=postgres
    - POSTGRES_DB=auth_db
  volumes:
    - postgres-data:/var/lib/postgresql/data
  networks:
    - codelab-network
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]
    interval: 10s
    timeout: 5s
    retries: 5

redis:
  image: redis:7-alpine
  networks:
    - codelab-network
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5

volumes:
  postgres-data:
```

---

## 13. Структура проекта

```
codelab-ai-service/
└── auth-service/
    ├── Dockerfile
    ├── pyproject.toml
    ├── uv.lock
    ├── .env.example
    ├── .dockerignore
    ├── .gitignore
    ├── README.md
    ├── docs/
    │   ├── TECHNICAL_SPECIFICATION.md
    │   ├── IMPLEMENTATION_PLAN.md
    │   └── API_DOCUMENTATION.md
    ├── alembic/
    │   ├── versions/
    │   ├── env.py
    │   └── script.py.mako
    ├── alembic.ini
    ├── app/
    │   ├── __init__.py
    │   ├── main.py
    │   ├── api/
    │   │   ├── __init__.py
    │   │   └── v1/
    │   │       ├── __init__.py
    │   │       ├── endpoints.py
    │   │       ├── oauth.py
    │   │       └── jwks.py
    │   ├── core/
    │   │   ├── __init__.py
    │   │   ├── config.py
    │   │   ├── dependencies.py
    │   │   └── security.py
    │   ├── models/
    │   │   ├── __init__.py
    │   │   ├── database.py
    │   │   ├── user.py
    │   │   ├── oauth_client.py
    │   │   ├── refresh_token.py
    │   │   └── audit_log.py
    │   ├── schemas/
    │   │   ├── __init__.py
    │   │   ├── token.py
    │   │   ├── user.py
    │   │   └── oauth.py
    │   ├── services/
    │   │   ├── __init__.py
    │   │   ├── auth_service.py
    │   │   ├── token_service.py
    │   │   ├── user_service.py
    │   │   ├── jwks_service.py
    │   │   ├── rate_limiter.py
    │   │   └── audit_service.py
    │   └── utils/
    │       ├── __init__.py
    │       ├── crypto.py
    │       └── validators.py
    └── tests/
        ├── __init__.py
        ├── conftest.py
        ├── test_oauth.py
        ├── test_token_service.py
        ├── test_user_service.py
        └── test_security.py
```

---

## 14. Критерии приёмки MVP

Auth Service считается реализованным, если:

- ✅ Пользователь может получить access/refresh token по login/password
- ✅ Resource service (Gateway) может валидировать JWT через JWKS
- ✅ Refresh token корректно ротируется при обновлении
- ✅ Обнаруживается повторное использование refresh token
- ✅ Rate limiting работает корректно
- ✅ Auth Service масштабируется горизонтально (stateless)
- ✅ Все тесты проходят (coverage > 80%)
- ✅ Документация API актуальна
- ✅ Миграции БД работают корректно
- ✅ Health check endpoint работает

---

## 15. План развития после MVP

### Фаза 2: Authorization Code Flow
- Реализация Authorization Code Grant + PKCE
- UI для consent screen
- Поддержка redirect_uri

### Фаза 3: Client Credentials
- Межсервисная аутентификация
- Service accounts

### Фаза 4: RBAC
- Роли и разрешения
- Иерархия ролей
- Admin UI для управления

### Фаза 5: SSO
- Интеграция с внешними IdP (Google, GitHub)
- SAML 2.0 поддержка
- OpenID Connect

### Фаза 6: Advanced Security
- Multi-factor authentication (MFA)
- Device fingerprinting
- Anomaly detection

---

## 16. Нефункциональные требования

### 16.1 Производительность
- ⚡ Время ответа `/oauth/token` < 200 мс (p95)
- ⚡ Throughput: 100 RPS на инстанс
- ⚡ Latency JWKS endpoint < 50 мс

### 16.2 Надежность
- 🛡️ Доступность: 99.9% (SLA)
- 🛡️ RPO (Recovery Point Objective): 1 час
- 🛡️ RTO (Recovery Time Objective): 15 минут

### 16.3 Масштабируемость
- 📈 Горизонтальное масштабирование (stateless)
- 📈 Поддержка 10,000+ активных пользователей
- 📈 Database sharding ready

### 16.4 Мониторинг
- 📊 Prometheus metrics
- 📊 Structured logging (JSON)
- 📊 Distributed tracing (OpenTelemetry)
- 📊 Alerting на критические события

---

## 17. Зависимости

### 17.1 Python пакеты

```toml
[project]
dependencies = [
    "fastapi==0.104.1",
    "uvicorn==0.24.0",
    "python-dotenv==1.0.0",
    "pydantic==2.5.1",
    "pydantic-settings==2.1.0",
    "sqlalchemy==2.0.23",
    "alembic==1.13.0",
    "asyncpg==0.29.0",
    "redis==5.0.1",
    "python-jose[cryptography]==3.3.0",
    "passlib[bcrypt]==1.7.4",
    "httpx==0.25.1",
]
```

### 17.2 Внешние сервисы

- PostgreSQL 16+
- Redis 7+

---

## 18. Миграция с текущей системы

### 18.1 Переходный период

**Этап 1: Параллельная работа**
- Auth Service развернут, но не используется
- Существующая аутентификация через `X-Internal-Auth` работает
- Тестирование Auth Service

**Этап 2: Постепенный переход**
- Gateway поддерживает оба метода аутентификации
- Flutter клиент обновлен для использования OAuth2
- Мониторинг обоих методов

**Этап 3: Полный переход**
- Все клиенты используют OAuth2
- `X-Internal-Auth` остается только для межсервисного взаимодействия
- Старый код удален

### 18.2 Обратная совместимость

```python
# Gateway middleware с поддержкой обоих методов
class HybridAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Попробовать JWT
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return await self.validate_jwt(request, call_next)
        
        # Fallback на X-Internal-Auth
        internal_auth = request.headers.get("X-Internal-Auth")
        if internal_auth == AppConfig.INTERNAL_API_KEY:
            return await call_next(request)
        
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
```

---

## 19. Тестирование

### 19.1 Unit тесты
- Все сервисы покрыты тестами (coverage > 80%)
- Тесты криптографических функций
- Тесты валидации

### 19.2 Integration тесты
- Полный OAuth2 flow (password grant)
- Refresh token rotation
- JWKS endpoint
- Rate limiting

### 19.3 Security тесты
- Brute-force защита
- SQL injection
- JWT tampering
- Refresh token reuse detection

### 19.4 Performance тесты
- Load testing (100 RPS)
- Stress testing
- Latency benchmarks

---

## 20. Документация

### 20.1 Обязательная документация

- ✅ API документация (OpenAPI/Swagger)
- ✅ Руководство по развертыванию
- ✅ Руководство по миграции БД
- ✅ Примеры интеграции для клиентов
- ✅ Troubleshooting guide

### 20.2 Примеры кода

**Flutter клиент:**
```dart
// Пример интеграции с Auth Service
class AuthService {
  Future<TokenResponse> login(String username, String password) async {
    final response = await http.post(
      Uri.parse('https://auth.codelab.local/oauth/token'),
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: {
        'grant_type': 'password',
        'username': username,
        'password': password,
        'client_id': 'codelab-flutter-app',
        'scope': 'api:read api:write',
      },
    );
    
    return TokenResponse.fromJson(jsonDecode(response.body));
  }
}
```

---

## 21. Примечания

### 21.1 Password Grant

Password Grant используется **временно**, исключительно для MVP и внутренних клиентов. Архитектура сервиса не должна препятствовать его последующему отключению в пользу Authorization Code Flow + PKCE.

### 21.2 Безопасность паролей

Требования к паролям (рекомендуется):
- Минимум 8 символов
- Хотя бы одна заглавная буква
- Хотя бы одна цифра
- Хотя бы один специальный символ

### 21.3 Ротация ключей

Процедура ротации RSA ключей:
1. Сгенерировать новую пару ключей с новым `kid`
2. Добавить публичный ключ в JWKS
3. Начать подписывать новые токены новым ключом
4. Старый ключ остается в JWKS для валидации существующих токенов
5. Через время жизни access token (15 минут) старый ключ можно удалить

---

## 22. Swagger UI и OpenAPI документация

### 22.1 OAuth2 Bearer интеграция

Swagger UI поддерживает интеграцию с OAuth2 Bearer токенами для тестирования защищённых эндпоинтов:

**Доступ к документации:**
```
http://localhost:8003/docs       # Swagger UI
http://localhost:8003/redoc      # ReDoc
```

### 22.2 Использование Authorize в Swagger UI

1. **Открыть Swagger UI:** `http://localhost:8003/docs`
2. **Нажать кнопку "Authorize"** в верхнем правом углу
3. **Получить токен:**
   - Использовать эндпоинт `POST /oauth/token` с тестовыми учётными данными:
   ```bash
   curl -X POST http://localhost:8003/api/v1/oauth/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=password" \
     -d "username=testuser" \
     -d "password=password123" \
     -d "client_id=codelab-flutter-app"
   ```
4. **Скопировать access_token** из ответа
5. **Вставить в диалоговое окно авторизации** (только значение токена без "Bearer")
6. **Нажать "Authorize"** — заголовок `Authorization: Bearer <token>` будет автоматически добавлен ко всем запросам

### 22.3 Управление Swagger UI

Swagger UI можно отключить в production через переменную окружения:

```bash
# Включить (по умолчанию для development)
AUTH_SERVICE__ENABLE_SWAGGER_UI=true

# Отключить (рекомендуется для production)
AUTH_SERVICE__ENABLE_SWAGGER_UI=false
```

При отключении `ENABLE_SWAGGER_UI=false`:
- `/docs` и `/redoc` возвращают 404
- API endpoints продолжают работать как обычно
- OpenAPI схема остаётся доступной через `/openapi.json` (может быть отключено настройкой FastAPI)

### 22.4 Security Scheme в OpenAPI

OpenAPI схема включает определение Bearer токена:

```json
{
  "components": {
    "securitySchemes": {
      "Bearer": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "OAuth2 Bearer token for API authentication"
      }
    }
  }
}
```

Защищённые эндпоинты автоматически помечаются с требованием Bearer токена:
- `/api/v1/oauth/sessions` — все методы требуют авторизации
- `/api/v1/auth/password-reset/confirm` — требует авторизации

---

## 23. Контакты и поддержка

**Разработчик:** Sergey Penkovsky  
**Email:** sergey.penkovsky@gmail.com  
**Проект:** CodeLab  
**Версия документа:** 1.0  
**Дата:** 2026-01-05
