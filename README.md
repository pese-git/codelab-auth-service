# Auth Service - OAuth2 Authorization Server для CodeLab

## Обзор

Auth Service — это микросервис аутентификации и авторизации для платформы CodeLab, реализующий OAuth2 Authorization Server с поддержкой Password Grant и Refresh Token Grant.

## Основные возможности

- ✅ OAuth2 Password Grant для аутентификации пользователей
- ✅ Refresh Token Grant с автоматической ротацией
- ✅ JWT токены с RS256 подписью
- ✅ JWKS endpoint для валидации токенов
- ✅ Rate limiting и brute-force защита
- ✅ Аудит логирование всех операций
- ✅ Горизонтальное масштабирование (stateless)

## Технологический стек

- **Python 3.12**
- **FastAPI** — веб-фреймворк
- **SQLite** — база данных (с возможностью миграции на PostgreSQL)
- **Redis** — кэширование и rate limiting
- **SQLAlchemy** — ORM
- **Alembic** — миграции БД
- **bcrypt** — хэширование паролей
- **python-jose** — JWT токены

## Быстрый старт

### Требования

- Docker и Docker Compose
- Python 3.12+ (для локальной разработки)

### Запуск с Docker Compose

```bash
# Из корневой директории проекта
cd codelab-ai-service

# Запустить все сервисы
docker-compose up -d

# Проверить статус
docker-compose ps

# Проверить логи Auth Service
docker-compose logs -f auth-service
```

Auth Service будет доступен на `http://localhost:8003`

### Первый запуск

1. **Применить миграции:**
```bash
docker-compose exec auth-service alembic upgrade head
```

2. **Создать тестового пользователя:**
```bash
docker-compose exec auth-service python -m app.scripts.create_user \
  --username testuser \
  --email test@example.com \
  --password password123
```

3. **Проверить health check:**
```bash
curl http://localhost:8003/health
```

## API Endpoints

### OAuth2 Token Endpoint

**POST /oauth/token**

Получение access и refresh токенов.

#### Password Grant

```bash
curl -X POST http://localhost:8003/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "username=test@example.com" \
  -d "password=password123" \
  -d "client_id=codelab-flutter-app" \
  -d "scope=api:read api:write"
```

**Ответ:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900,
  "scope": "api:read api:write"
}
```

#### Refresh Token Grant

```bash
curl -X POST http://localhost:8003/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d "client_id=codelab-flutter-app"
```

### JWKS Endpoint

**GET /.well-known/jwks.json**

Публичные ключи для валидации JWT токенов.

```bash
curl http://localhost:8003/.well-known/jwks.json
```

**Ответ:**
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

### Health Check

**GET /health**

```bash
curl http://localhost:8003/health
```

**Ответ:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "connected",
  "redis": "connected"
}
```

## Password Reset API

Auth Service предоставляет защищенные endpoints для сброса пароля пользователя:

### Endpoints

**POST /api/v1/auth/password-reset/request** — Запрос на сброс пароля

```bash
curl -X POST http://localhost:8003/api/v1/auth/password-reset/request \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

**Ответ (200 OK):**
```json
{
  "message": "If an account with that email exists, you will receive password reset instructions."
}
```

**POST /api/v1/auth/password-reset/confirm** — Подтверждение сброса пароля

```bash
curl -X POST http://localhost:8003/api/v1/auth/password-reset/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    "password": "NewPassword123!",
    "password_confirm": "NewPassword123!"
  }'
```

**Ответ (200 OK):**
```json
{
  "message": "Password changed successfully"
}
```

### Error Codes

- **400 Bad Request** — Невалидный email, пароль не соответствует требованиям, токен истек
  ```json
  {
    "detail": "Password does not meet requirements: minimum 8 characters, at least one uppercase, one digit and one special character"
  }
  ```

- **429 Too Many Requests** — Превышен лимит запросов
  ```json
  {
    "detail": "Too many password reset requests. Please try again later."
  }
  ```

### Flow: Запрос → Email → Подтверждение

1. **Запрос сброса пароля:**
   - Пользователь отправляет POST на `/api/v1/auth/password-reset/request` с email
   - Система генерирует одноразовый токен (действует 30 минут)
   - Отправляется письмо с ссылкой для подтверждения (асинхронно)
   - Всегда возвращается 200 OK (безопасность: не раскрываем наличие пользователя)

2. **Лимиты (Rate Limiting):**
   - **Запрос:** максимум 3 запроса за час на email-адрес
   - **Подтверждение:** максимум 10 попыток за 5 минут на IP-адрес
   - При превышении лимита: 429 Too Many Requests

3. **Подтверждение сброса пароля:**
   - Пользователь открывает ссылку из письма (содержит токен)
   - Отправляет новый пароль на `/api/v1/auth/password-reset/confirm`
   - Пароль должен соответствовать требованиям (8+ символов, заглавная, цифра, спецсимвол)
   - Токен помечается как использованный (одноразовый)
   - При успехе пользователь может войти с новым паролем

### Требования к паролю

- Минимум 8 символов
- Хотя бы одна заглавная буква (A-Z)
- Хотя бы одна цифра (0-9)
- Хотя бы один специальный символ (!@#$%^&*)

## Email Notifications

Auth Service включает интеграцию SMTP для отправки email уведомлений при важных событиях в системе:

- **Welcome emails** — отправляются при успешной регистрации пользователя
- **Email confirmation** — письмо с ссылкой подтверждения для верификации email адреса
- **Password reset** — письмо с защищенной ссылкой для сброса пароля

### API Endpoints для Email и Регистрации

**POST /api/v1/register** — Регистрация пользователя с отправкой welcome и confirmation email

```bash
curl -X POST http://localhost:8003/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "username": "newuser",
    "password": "SecurePassword123"
  }'
```

**Ответ (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "newuser@example.com",
  "username": "newuser",
  "created_at": "2026-03-25T13:50:00.000Z"
}
```

**Требования для пароля при регистрации:**
- Минимум 8 символов
- Максимум 128 символов

**Ошибки:**
- **409 Conflict** — Email или username уже зарегистрированы
- **422 Unprocessable Entity** — Невалидные данные (неправильный формат email, короткий пароль и т.д.)

**GET /api/v1/confirm-email** — Подтверждение email адреса по токену

```bash
# Пример подтверждения email
curl "http://localhost:8003/api/v1/confirm-email?token=<confirmation_token>"
```

**Ответ (200 OK):**
```json
{
  "message": "Email confirmed successfully"
}
```

### Конфигурация SMTP

Настройте SMTP через переменные окружения:

```bash
# SMTP сервер
AUTH_SERVICE__SMTP_HOST=smtp.gmail.com
AUTH_SERVICE__SMTP_PORT=587
AUTH_SERVICE__SMTP_USERNAME=your-email@gmail.com
AUTH_SERVICE__SMTP_PASSWORD=your-app-password
AUTH_SERVICE__SMTP_FROM_EMAIL=noreply@codelab.com

# SMTP опции
AUTH_SERVICE__SMTP_USE_TLS=true          # Использовать STARTTLS
AUTH_SERVICE__SMTP_TIMEOUT=30            # Timeout в секундах
AUTH_SERVICE__SMTP_MAX_RETRIES=3         # Максимум попыток отправки

# Управление отправкой
AUTH_SERVICE__SEND_WELCOME_EMAIL=true           # Отправлять приветственные письма
AUTH_SERVICE__REQUIRE_EMAIL_CONFIRMATION=true   # Требовать подтверждение email
AUTH_SERVICE__SEND_PASSWORD_RESET_EMAIL=true    # Отправлять письма сброса пароля
```

### Локальная разработка с MailHog

Для локальной разработки используйте MailHog — fake SMTP сервер:

```bash
# Запустить MailHog (используется в docker-compose.yml)
docker-compose up mailhog

# Web UI для просмотра писем: http://localhost:1025
# SMTP сервер: localhost:1025
```

Обновите `.env` для разработки:

```bash
AUTH_SERVICE__SMTP_HOST=mailhog
AUTH_SERVICE__SMTP_PORT=1025
AUTH_SERVICE__SMTP_USERNAME=          # MailHog не требует аутентификации
AUTH_SERVICE__SMTP_PASSWORD=
AUTH_SERVICE__SMTP_USE_TLS=false
```

Для получения более полной информации по настройке SMTP для различных провайдеров (SendGrid, AWS SES, Mailgun) см. [Email Setup Guide](docs/EMAIL_SETUP.md).

## Документация

### Основные документы

- [**Техническое задание**](docs/TECHNICAL_SPECIFICATION.md) — полное ТЗ с требованиями
- [**План реализации**](docs/IMPLEMENTATION_PLAN.md) — пошаговый план разработки
- [**Интеграционные точки**](docs/INTEGRATION_POINTS.md) — интеграция с другими сервисами

### Дополнительные документы

- [**API Documentation (Swagger/OpenAPI)**](#api-endpoints) — интерактивная API документация
- [**Руководство по email**](docs/EMAIL_SETUP.md) — настройка различных SMTP провайдеров
- [**QA отчеты**](docs/QA_REPORT_SMTP.md) — результаты тестирования
- Руководство по развертыванию
- Руководство по интеграции для клиентов
- Troubleshooting guide

## Структура проекта

```
auth-service/
├── app/
│   ├── api/              # API endpoints
│   │   └── v1/
│   │       ├── oauth.py  # OAuth2 endpoints
│   │       └── jwks.py   # JWKS endpoint
│   ├── core/             # Конфигурация и безопасность
│   │   ├── config.py
│   │   └── security.py
│   ├── models/           # SQLAlchemy модели
│   │   ├── user.py
│   │   ├── oauth_client.py
│   │   └── refresh_token.py
│   ├── schemas/          # Pydantic схемы
│   ├── services/         # Бизнес-логика
│   │   ├── auth_service.py
│   │   ├── token_service.py
│   │   └── user_service.py
│   └── utils/            # Утилиты
├── alembic/              # Миграции БД
├── tests/                # Тесты
├── docs/                 # Документация
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Разработка

### Локальная разработка

```bash
# Установить зависимости
uv sync

# Запустить сервер
uv run uvicorn app.main:app --reload --port 8003

# Запустить тесты
uv run pytest

# Проверить coverage
uv run pytest --cov=app --cov-report=html

# Линтинг
uv run ruff check app/
```

### Создание миграции

```bash
# Создать новую миграцию
alembic revision --autogenerate -m "Description"

# Применить миграции
alembic upgrade head

# Откатить миграцию
alembic downgrade -1
```

### Генерация RSA ключей

```bash
# Сгенерировать новую пару ключей
python -m app.scripts.generate_keys --output-dir ./keys
```

## Конфигурация

### Переменные окружения

```bash
# Основные настройки
ENVIRONMENT=development
PORT=8003

# База данных
AUTH_SERVICE__DB_URL=sqlite:///data/auth.db

# Redis
AUTH_SERVICE__REDIS_URL=redis://redis:6379/1

# JWT настройки
AUTH_SERVICE__JWT_ISSUER=https://auth.codelab.local
AUTH_SERVICE__JWT_AUDIENCE=codelab-api
AUTH_SERVICE__ACCESS_TOKEN_LIFETIME=900        # 15 минут
AUTH_SERVICE__REFRESH_TOKEN_LIFETIME=2592000   # 30 дней

# RSA ключи
AUTH_SERVICE__PRIVATE_KEY_PATH=/app/keys/private_key.pem
AUTH_SERVICE__PUBLIC_KEY_PATH=/app/keys/public_key.pem

# Логирование
AUTH_SERVICE__LOG_LEVEL=DEBUG
```

## Безопасность

### Требования к паролям

- Минимум 8 символов
- Хотя бы одна заглавная буква
- Хотя бы одна цифра
- Хотя бы один специальный символ

### Rate Limiting

- **IP-based:** 5 запросов в минуту на `/oauth/token`
- **Username-based:** 10 запросов в час на `/oauth/token`

### Brute-force защита

- После 5 неудачных попыток — временная блокировка на 15 минут
- Логирование всех неудачных попыток

### JWT токены

- **Access Token:** 15 минут, RS256, не хранится в БД
- **Refresh Token:** 30 дней, RS256, одноразовый (rotation)

## Мониторинг

### Prometheus метрики

Доступны на `/metrics`:

- `auth_token_requests_total` — количество запросов токенов
- `auth_token_request_duration_seconds` — время обработки
- `auth_failed_login_attempts_total` — неудачные попытки входа
- `auth_refresh_token_rotations_total` — ротации refresh токенов

### Health Check

```bash
# Проверка здоровья сервиса
curl http://localhost:8003/health

# Проверка готовности (readiness probe)
curl http://localhost:8003/ready
```

## Тестирование

### Запуск тестов

```bash
# Все тесты
pytest

# С coverage
pytest --cov=app --cov-report=html

# Только unit тесты
pytest tests/unit/

# Только integration тесты
pytest tests/integration/

# Security тесты
pytest tests/security/
```

### Тестовые данные

Предустановленные OAuth клиенты:

- **codelab-flutter-app** — Flutter приложение (public client)
- **codelab-internal** — Внутренние сервисы (confidential client)

## Производительность

### Требования

- Время ответа `/oauth/token` < 200ms (p95)
- Throughput: 100 RPS на инстанс
- Latency JWKS endpoint < 50ms

### Оптимизация

- JWKS кэшируется в Redis (TTL 1 час)
- OAuth clients кэшируются (TTL 5 минут)
- SQLite в WAL режиме
- Connection pooling

## Масштабирование

Auth Service поддерживает горизонтальное масштабирование:

```yaml
# docker-compose.yml
services:
  auth-service:
    deploy:
      replicas: 3
```

**Важно:**
- Access токены stateless (не требуют синхронизации)
- Refresh токены хранятся в общей БД
- Redis используется для rate limiting и кэширования

## Миграция на PostgreSQL

Для production окружения рекомендуется PostgreSQL:

```bash
# 1. Обновить connection string
AUTH_SERVICE__DB_URL=postgresql://user:pass@postgres:5432/auth_db

# 2. Обновить типы данных в моделях
# String(36) → UUID

# 3. Применить миграции
alembic upgrade head
```

## Troubleshooting

### Проблема: Auth Service не запускается

```bash
# Проверить логи
docker-compose logs auth-service

# Проверить БД
docker-compose exec auth-service ls -la /app/data/

# Проверить Redis
docker-compose exec redis redis-cli ping
```

### Проблема: JWT токены не валидируются

```bash
# Проверить JWKS endpoint
curl http://localhost:8003/.well-known/jwks.json

# Проверить RSA ключи
docker-compose exec auth-service ls -la /app/keys/
```

### Проблема: Rate limiting не работает

```bash
# Проверить Redis
docker-compose exec redis redis-cli
> KEYS rate_limit:*
```

## Roadmap

### MVP (текущая версия)
- ✅ OAuth2 Password Grant
- ✅ Refresh Token Grant
- ✅ JWT токены (RS256)
- ✅ JWKS endpoint
- ✅ Rate limiting
- ✅ Аудит логирование

### Post-MVP
- [ ] Authorization Code Flow + PKCE
- [ ] Client Credentials Grant
- [ ] RBAC (Role-Based Access Control)
- [ ] SSO с внешними провайдерами
- [ ] Admin UI
- [ ] Multi-factor authentication (MFA)

## Лицензия

MIT License

## Контакты

**Разработчик:** Sergey Penkovsky  
**Email:** sergey.penkovsky@gmail.com  
**Проект:** CodeLab  
**Версия:** 0.1.0 (MVP)
