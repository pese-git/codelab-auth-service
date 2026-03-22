# Спецификация проекта: CodeLab Auth Service

**Версия:** 1.0.0  
**Статус:** ✅ Production Ready  
**Дата обновления:** 22 марта 2026

---

## 📋 Обзор проекта

**CodeLab Auth Service** — это микросервис аутентификации и авторизации, реализующий OAuth2 Authorization Server с поддержкой Password Grant и Refresh Token Grant. Сервис обеспечивает безопасную выдачу JWT токенов (RS256) и интегрируется с существующей микросервисной архитектурой платформы CodeLab.

### 🎯 Назначение

Централизованное управление аутентификацией и авторизацией для всех микросервисов CodeLab, обеспечивающее:
- ✅ Безопасную выдачу токенов доступа
- ✅ Управление сессиями пользователей
- ✅ Защиту от атак (rate limiting, brute-force protection)
- ✅ Аудит всех операций аутентификации
- ✅ Горизонтальное масштабирование (stateless дизайн)

---

## ⚡ Основные возможности (MVP)

### 1. OAuth2 Grant Types

| Grant Type | Описание | Статус |
|-----------|---------|--------|
| **Password Grant** | Аутентификация по username/password | ✅ Реализовано |
| **Refresh Token Grant** | Обновление access token | ✅ Реализовано |
| Authorization Code (PKCE) | Для веб-приложений | ⏳ Post-MVP |
| Client Credentials | Межсервисное взаимодействие | ⏳ Post-MVP |

### 2. JWT Токены

| Тип | Время жизни | Алгоритм | Хранение |
|-----|------------|---------|---------|
| **Access Token** | 15 минут | RS256 | Stateless (не хранится) |
| **Refresh Token** | 30 дней | RS256 | В БД (хэш jti) |

### 3. Безопасность

- 🛡️ **Rate Limiting**: 5 запросов/минуту на IP, 10/час на username
- 🛡️ **Brute-Force Protection**: блокировка после 5 неудачных попыток на 15 минут
- 🛡️ **Refresh Token Rotation**: одноразовые токены с обнаружением повторного использования
- 🛡️ **Криптография**: bcrypt (cost 12) для паролей, RS256 для JWT
- 🛡️ **Валидация входных данных**: email, пароль, scope

### 4. Интеграция

- 🔗 **Gateway**: JWT валидация через JWKS endpoint
- 🔗 **Agent Runtime**: JWT валидация, привязка сессий к пользователям
- 🔗 **LLM Proxy**: внутренняя аутентификация (X-Internal-Auth)
- 🔗 **Redis**: rate limiting, кэширование JWKS и OAuth клиентов
- 🔗 **SQLite/PostgreSQL**: хранение пользователей и токенов

### 5. Аудит и Логирование

- 📊 **Структурированное логирование**: JSON формат с correlation ID
- 📊 **Event Tracking**: login, token_refresh, token_revoke, security_incidents
- 📊 **Метрики**: Prometheus metrics для мониторинга

---

## 🔧 Технологический стек

### Backend

| Компонент | Выбор | Обоснование |
|-----------|-------|-------------|
| **Язык** | Python 3.12 | Совместимость с существующими сервисами |
| **Framework** | FastAPI 0.104.1 | Используется во всех сервисах CodeLab |
| **ORM** | SQLAlchemy 2.0 | Поддержка миграций, абстракция БД |
| **Миграции** | Alembic 1.13 | Управление схемой БД |
| **Криптография** | python-jose, bcrypt | Стандарт индустрии для JWT и паролей |

### Инфраструктура

| Компонент | Выбор | Обоснование |
|-----------|-------|-------------|
| **БД (Dev)** | SQLite | Простота развертывания, нулевая конфигурация |
| **БД (Prod)** | PostgreSQL 16+ | Production-ready, масштабируемость |
| **Cache/Rate Limiting** | Redis 7+ | In-memory, быстрый доступ |
| **Контейнеризация** | Docker | Единообразное развертывание |
| **Мониторинг** | Prometheus | Метрики и alerting |

### Зависимости (ключевые)

```toml
dependencies = [
    "fastapi==0.104.1",
    "uvicorn==0.24.0",
    "sqlalchemy==2.0.23",
    "alembic==1.13.0",
    "python-jose[cryptography]==3.3.0",
    "passlib[bcrypt]==1.7.4",
    "redis==5.0.1",
    "httpx==0.25.1",
    "pydantic==2.5.1",
    "pydantic-settings==2.1.0",
]
```

---

## 🏗️ Архитектурные принципы

### 1. Layered Architecture

```
┌─────────────────────────────────────────┐
│          API Layer (FastAPI)            │  HTTP endpoints, request/response
├─────────────────────────────────────────┤
│        Service Layer (Business Logic)    │  Auth, Token, User, OAuth Client
├─────────────────────────────────────────┤
│      Repository Layer (Data Access)      │  SQLAlchemy models, queries
├─────────────────────────────────────────┤
│     Infrastructure (External Services)   │  Redis, Database
└─────────────────────────────────────────┘
```

### 2. Dependency Injection

- ✅ FastAPI Depends для инъекции зависимостей
- ✅ Service-oriented архитектура
- ✅ Лёгкое тестирование компонентов

### 3. Stateless Design

- ✅ Access tokens не хранятся в БД
- ✅ Horizontally scalable (распределённое масштабирование)
- ✅ Общая БД для refresh tokens
- ✅ Redis для rate limiting и кэширования

### 4. Separation of Concerns

- ✅ API endpoints в `app/api/`
- ✅ Бизнес-логика в `app/services/`
- ✅ Модели данных в `app/models/`
- ✅ Утилиты в `app/utils/`
- ✅ Middleware в `app/middleware/`

---

## 📈 Roadmap и статус

### ✅ MVP (Реализовано)

**Статус:** Production Ready (январь 2026)

- ✅ OAuth2 Password Grant
- ✅ Refresh Token Grant с rotation
- ✅ JWT токены (RS256)
- ✅ JWKS endpoint (публичные ключи)
- ✅ Rate limiting (IP + username)
- ✅ Brute-force protection
- ✅ Refresh token reuse detection
- ✅ Аудит логирование
- ✅ Интеграция с Gateway
- ✅ Интеграция с Agent Runtime

### ⏳ Post-MVP Фаза 2 (4-6 недель)

- ⏳ Authorization Code Flow + PKCE
- ⏳ Consent screen UI
- ⏳ Redirect URI validation

### ⏳ Фаза 3: Client Credentials (2-3 недели)

- ⏳ Межсервисная аутентификация
- ⏳ Service accounts

### ⏳ Фаза 4: RBAC (4-6 недель)

- ⏳ Роли и разрешения
- ⏳ Иерархия ролей
- ⏳ Admin UI

### ⏳ Фаза 5: SSO (6-8 недель)

- ⏳ Google, GitHub OAuth
- ⏳ SAML 2.0
- ⏳ OpenID Connect

### ⏳ Фаза 6: Advanced Security (4-6 недель)

- ⏳ Multi-factor authentication (MFA)
- ⏳ Device fingerprinting
- ⏳ Anomaly detection

---

## 📊 Производительность и SLA

### Требования к производительности

| Метрика | Требование | Статус |
|---------|-----------|--------|
| **Latency /oauth/token** | < 200ms (p95) | ✅ Выполнено |
| **Latency /.well-known/jwks.json** | < 50ms (p95) | ✅ Выполнено |
| **Throughput** | > 100 RPS на инстанс | ✅ Выполнено |
| **Доступность** | 99.9% SLA | ✅ Достигнуто |

### Оптимизация

- 🚀 JWKS кэшируется в Redis (TTL 1 час)
- 🚀 OAuth clients кэшируются (TTL 5 минут)
- 🚀 Connection pooling для БД
- 🚀 Индексы на часто используемые поля
- 🚀 SQLite WAL режим (для dev)
- 🚀 Horizontal scaling через stateless дизайн

### Масштабирование

```
┌──────────────────────────────┐
│   Load Balancer (nginx)      │
├──────────────────────────────┤
│  Auth Service Instance 1     │  Stateless
│  Auth Service Instance 2     │  Shared DB
│  Auth Service Instance N     │  Shared Redis
├──────────────────────────────┤
│  PostgreSQL (Primary)        │  Single DB
│  PostgreSQL (Standby)        │  HA Setup
├──────────────────────────────┤
│  Redis Cluster               │  Cache + Rate Limiting
└──────────────────────────────┘
```

---

## 📝 Структура проекта

```
codelab-auth-service/
├── .roo/                          # Roo конфигурация
├── openspec/                      # OpenSpec спецификации
│   ├── specs/
│   │   ├── project.md            # ← Этот файл
│   │   ├── architecture.md       
│   │   ├── data-models.md        
│   │   ├── api.md                
│   │   ├── security.md           
│   │   ├── integration.md        
│   │   └── configuration.md      
│   └── config.yaml
├── docs/                          # Документация
│   ├── PROJECT_SUMMARY.md
│   ├── TECHNICAL_SPECIFICATION.md
│   ├── IMPLEMENTATION_PLAN.md
│   └── INTEGRATION_POINTS.md
├── app/                           # Исходный код
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   └── v1/
│   │       ├── oauth.py
│   │       └── jwks.py
│   ├── core/
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   └── security.py
│   ├── models/
│   │   ├── user.py
│   │   ├── oauth_client.py
│   │   ├── refresh_token.py
│   │   └── audit_log.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── token_service.py
│   │   ├── user_service.py
│   │   ├── oauth_client_service.py
│   │   ├── refresh_token_service.py
│   │   ├── jwks_service.py
│   │   ├── rate_limiter.py
│   │   ├── brute_force_protection.py
│   │   └── audit_service.py
│   ├── middleware/
│   │   ├── logging.py
│   │   └── rate_limit.py
│   ├── schemas/
│   │   ├── user.py
│   │   ├── oauth.py
│   │   └── token.py
│   └── utils/
│       ├── crypto.py
│       └── validators.py
├── alembic/                       # Миграции БД
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── scripts/
│   ├── generate_keys.py           # Генерация RSA ключей
│   └── init_db.py                 # Инициализация БД
├── tests/                         # Тесты
│   ├── conftest.py
│   ├── test_oauth.py
│   ├── test_token_service.py
│   └── ...
├── pyproject.toml                 # Зависимости
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🔗 Связанные спецификации

| Документ | Описание | Статус |
|----------|---------|--------|
| [`architecture.md`](architecture.md) | Детальная архитектура, паттерны, компоненты | ✅ |
| [`data-models.md`](data-models.md) | ER диаграмма, таблицы, миграции | ✅ |
| [`api.md`](api.md) | API контракты, endpoints, примеры | ✅ |
| [`security.md`](security.md) | Криптография, rate limiting, защита | ✅ |
| [`integration.md`](integration.md) | Интеграция с Gateway и Agent Runtime | ✅ |
| [`configuration.md`](configuration.md) | Переменные окружения, конфигурация | ✅ |

---

## 👥 Команда и ответственность

| Роль | FTE | Ответственность |
|------|-----|-----------------|
| **Backend Developer** | 1.0 | Разработка, тестирование, документация |
| **DevOps Engineer** | 0.5 | Инфраструктура, Docker, мониторинг |
| **QA Engineer** | 0.5 | Тестирование, security тесты |

**Итого:** 2 FTE  
**Длительность MVP:** 6-8 недель (25-40 рабочих дней)

---

## ✅ Критерии успеха

### Функциональные требования
- ✅ Пользователь может получить access/refresh token по login/password
- ✅ Gateway валидирует JWT через JWKS
- ✅ Refresh token ротируется корректно
- ✅ Reuse detection обнаруживает атаки
- ✅ Rate limiting и brute-force защита работают

### Нефункциональные требования
- ✅ Время ответа < 200ms (p95)
- ✅ Throughput > 100 RPS
- ✅ Coverage > 80%
- ✅ Доступность > 99.9%

### Безопасность
- ✅ Все тесты на безопасность проходят
- ✅ Code review с фокусом на security
- ✅ Нет SQL injection, JWT tampering уязвимостей
- ✅ Правильное хэширование паролей и токенов

---

## 📞 Контакты и поддержка

**Разработчик:** Sergey Penkovsky  
**Email:** sergey.penkovsky@gmail.com  
**Проект:** CodeLab Authentication Service  
**GitHub:** `codelab-auth-service`  
**Version:** 1.0.0  
**Last Updated:** 2026-03-22

---

## 📖 Дополнительные ресурсы

- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [JWT RFC 7519](https://tools.ietf.org/html/rfc7519)
- [JWKS Specification](https://tools.ietf.org/html/rfc7517)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
