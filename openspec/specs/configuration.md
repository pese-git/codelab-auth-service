# Спецификация конфигурации

**Версия:** 1.0.0  
**Статус:** ✅ Production Ready  
**Дата обновления:** 22 марта 2026

---

## ⚙️ Обзор конфигурации

CodeLab Auth Service конфигурируется через переменные окружения. Поддерживаются разные конфигурации для разработки (dev), staging и production окружений.

**Ключевые принципы:**
- ✅ 12-factor app methodology
- ✅ Все конфигурация через переменные окружения
- ✅ Безопасные значения по умолчанию
- ✅ Валидация конфигурации при старте
- ✅ Поддержка разных БД (SQLite/PostgreSQL)

---

## 📋 Переменные окружения

### 1. Базовая конфигурация приложения

| Переменная | Тип | Default | Описание | Dev | Staging | Prod |
|-----------|-----|---------|---------|-----|---------|------|
| `ENVIRONMENT` | string | `development` | Окружение приложения | `development` | `staging` | `production` |
| `DEBUG` | bool | `true` | Режим отладки | `true` | `false` | `false` |
| `PORT` | int | `8003` | Порт приложения | `8003` | `8003` | `8003` |
| `HOST` | string | `0.0.0.0` | IP адрес | `0.0.0.0` | `0.0.0.0` | `0.0.0.0` |
| `LOG_LEVEL` | string | `INFO` | Уровень логирования | `DEBUG` | `INFO` | `WARNING` |
| `WORKERS` | int | `1` | Количество worker процессов | `1` | `4` | `8` |

**Примеры:**
```bash
# Dev
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Prod
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
```

### 2. База данных

| Переменная | Тип | Default | Описание |
|-----------|-----|---------|---------|
| `AUTH_SERVICE__DB_URL` | string | `sqlite:///data/auth.db` | Connection string БД |
| `AUTH_SERVICE__DB_ECHO` | bool | `false` | Логировать SQL запросы |
| `AUTH_SERVICE__DB_POOL_SIZE` | int | `5` | Размер connection pool |
| `AUTH_SERVICE__DB_MAX_OVERFLOW` | int | `10` | Максимум overflow соединений |
| `AUTH_SERVICE__DB_POOL_RECYCLE` | int | `3600` | Переиспользование соединения (сек) |

**Примеры:**

```bash
# SQLite (Development)
AUTH_SERVICE__DB_URL=sqlite:///data/auth.db

# PostgreSQL (Production)
AUTH_SERVICE__DB_URL=postgresql://user:password@pg-host:5432/auth_db
AUTH_SERVICE__DB_POOL_SIZE=20
AUTH_SERVICE__DB_MAX_OVERFLOW=40
```

**Миграция SQLite → PostgreSQL:**
```bash
# Автоматическая миграция при смене DB_URL
# Alembic применяет миграции к новой БД
docker-compose exec auth-service alembic upgrade head
```

### 3. Redis

| Переменная | Тип | Default | Описание |
|-----------|-----|---------|---------|
| `AUTH_SERVICE__REDIS_URL` | string | `redis://localhost:6379/0` | Connection string Redis |
| `AUTH_SERVICE__REDIS_TIMEOUT` | int | `5` | Timeout (сек) |
| `AUTH_SERVICE__REDIS_DB` | int | `0` | Database number |

**Примеры:**

```bash
# Local (Development)
AUTH_SERVICE__REDIS_URL=redis://localhost:6379/0

# Docker Compose
AUTH_SERVICE__REDIS_URL=redis://redis:6379/1

# Cluster (Production)
AUTH_SERVICE__REDIS_URL=redis://redis-cluster:6379/0
```

### 4. JWT конфигурация

| Переменная | Тип | Default | Описание |
|-----------|-----|---------|---------|
| `AUTH_SERVICE__JWT_ISSUER` | string | `https://auth.codelab.local` | Издатель JWT |
| `AUTH_SERVICE__JWT_AUDIENCE` | string | `codelab-api` | Аудитория JWT |
| `AUTH_SERVICE__ACCESS_TOKEN_LIFETIME` | int | `900` | Время жизни access token (сек) |
| `AUTH_SERVICE__REFRESH_TOKEN_LIFETIME` | int | `2592000` | Время жизни refresh token (сек) |
| `AUTH_SERVICE__PRIVATE_KEY_PATH` | string | `/app/keys/private_key.pem` | Путь к приватному ключу |
| `AUTH_SERVICE__PUBLIC_KEY_PATH` | string | `/app/keys/public_key.pem` | Путь к публичному ключу |
| `AUTH_SERVICE__KEY_ROTATION_DAYS` | int | `90` | Период ротации ключей (дни) |

**Примеры:**

```bash
# Development
AUTH_SERVICE__JWT_ISSUER=https://auth.localhost
AUTH_SERVICE__ACCESS_TOKEN_LIFETIME=900
AUTH_SERVICE__REFRESH_TOKEN_LIFETIME=2592000

# Production
AUTH_SERVICE__JWT_ISSUER=https://auth.codelab.local
AUTH_SERVICE__ACCESS_TOKEN_LIFETIME=900
AUTH_SERVICE__REFRESH_TOKEN_LIFETIME=2592000
AUTH_SERVICE__PRIVATE_KEY_PATH=/app/keys/prod/private_key.pem
```

**Значения по умолчанию:**
- Access Token: 15 минут (900 сек)
- Refresh Token: 30 дней (2,592,000 сек)

### 5. Безопасность

| Переменная | Тип | Default | Описание |
|-----------|-----|---------|---------|
| `AUTH_SERVICE__BCRYPT_ROUNDS` | int | `12` | Cost factor для bcrypt |
| `AUTH_SERVICE__PASSWORD_MIN_LENGTH` | int | `8` | Минимальная длина пароля |
| `AUTH_SERVICE__RATE_LIMIT_IP_PER_MINUTE` | int | `5` | Лимит по IP в минуту |
| `AUTH_SERVICE__RATE_LIMIT_USERNAME_PER_HOUR` | int | `10` | Лимит по username в час |
| `AUTH_SERVICE__BRUTE_FORCE_THRESHOLD` | int | `5` | Порог блокировки |
| `AUTH_SERVICE__BRUTE_FORCE_LOCKOUT_MINUTES` | int | `15` | Длительность блокировки |
| `AUTH_SERVICE__REQUIRE_HTTPS` | bool | `true` | Требовать HTTPS |
| `AUTH_SERVICE__CORS_ORIGINS` | string | `*` | CORS origins (comma-separated) |

**Примеры:**

```bash
# Development (permissive)
AUTH_SERVICE__BCRYPT_ROUNDS=10
AUTH_SERVICE__RATE_LIMIT_IP_PER_MINUTE=100
AUTH_SERVICE__REQUIRE_HTTPS=false
AUTH_SERVICE__CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Production (strict)
AUTH_SERVICE__BCRYPT_ROUNDS=12
AUTH_SERVICE__RATE_LIMIT_IP_PER_MINUTE=5
AUTH_SERVICE__REQUIRE_HTTPS=true
AUTH_SERVICE__CORS_ORIGINS=https://app.codelab.local
```

### 6. Логирование

| Переменная | Тип | Default | Описание |
|-----------|-----|---------|---------|
| `LOG_LEVEL` | string | `INFO` | Уровень логирования |
| `AUTH_SERVICE__LOG_FORMAT` | string | `json` | Формат логов (json/text) |
| `AUTH_SERVICE__LOG_FILE` | string | `null` | Файл логов (если не null) |
| `AUTH_SERVICE__SENTRY_DSN` | string | `` | Sentry DSN для error tracking |

**Примеры:**

```bash
# Development
LOG_LEVEL=DEBUG
AUTH_SERVICE__LOG_FORMAT=text

# Production
LOG_LEVEL=WARNING
AUTH_SERVICE__LOG_FORMAT=json
AUTH_SERVICE__SENTRY_DSN=https://xxxxx@sentry.io/12345
```

---

## 📝 Файл .env.example

```bash
# ============================================================================
# CodeLab Auth Service Configuration
# ============================================================================
# Copy this file to .env and fill in the values

# ============================================================================
# Environment
# ============================================================================
ENVIRONMENT=development
DEBUG=true
PORT=8003
HOST=0.0.0.0
LOG_LEVEL=DEBUG

# ============================================================================
# Database Configuration
# ============================================================================
# SQLite (Development)
AUTH_SERVICE__DB_URL=sqlite:///data/auth.db
# PostgreSQL (Production)
# AUTH_SERVICE__DB_URL=postgresql://user:password@localhost:5432/auth_db

AUTH_SERVICE__DB_ECHO=false
AUTH_SERVICE__DB_POOL_SIZE=5
AUTH_SERVICE__DB_MAX_OVERFLOW=10
AUTH_SERVICE__DB_POOL_RECYCLE=3600

# ============================================================================
# Redis Configuration
# ============================================================================
AUTH_SERVICE__REDIS_URL=redis://localhost:6379/0
AUTH_SERVICE__REDIS_TIMEOUT=5
AUTH_SERVICE__REDIS_DB=0

# ============================================================================
# JWT Configuration
# ============================================================================
AUTH_SERVICE__JWT_ISSUER=https://auth.localhost
AUTH_SERVICE__JWT_AUDIENCE=codelab-api
AUTH_SERVICE__ACCESS_TOKEN_LIFETIME=900
AUTH_SERVICE__REFRESH_TOKEN_LIFETIME=2592000
AUTH_SERVICE__PRIVATE_KEY_PATH=./keys/private_key.pem
AUTH_SERVICE__PUBLIC_KEY_PATH=./keys/public_key.pem
AUTH_SERVICE__KEY_ROTATION_DAYS=90

# ============================================================================
# Security Configuration
# ============================================================================
AUTH_SERVICE__BCRYPT_ROUNDS=12
AUTH_SERVICE__PASSWORD_MIN_LENGTH=8
AUTH_SERVICE__RATE_LIMIT_IP_PER_MINUTE=5
AUTH_SERVICE__RATE_LIMIT_USERNAME_PER_HOUR=10
AUTH_SERVICE__BRUTE_FORCE_THRESHOLD=5
AUTH_SERVICE__BRUTE_FORCE_LOCKOUT_MINUTES=15
AUTH_SERVICE__REQUIRE_HTTPS=false
AUTH_SERVICE__CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# ============================================================================
# Logging Configuration
# ============================================================================
AUTH_SERVICE__LOG_FORMAT=json
AUTH_SERVICE__LOG_FILE=
# AUTH_SERVICE__SENTRY_DSN=https://xxxxx@sentry.io/12345

# ============================================================================
# Integration Configuration
# ============================================================================
# Gateway
GATEWAY__AUTH_SERVICE_URL=http://localhost:8003
GATEWAY__USE_JWT_AUTH=false

# Agent Runtime
AGENT_RUNTIME__AUTH_SERVICE_URL=http://localhost:8003
AGENT_RUNTIME__USE_JWT_AUTH=false
```

---

## 🐳 Docker Compose конфигурация

### docker-compose.yml

```yaml
version: '3.8'

services:
  auth-service:
    build:
      context: ./auth-service
      dockerfile: Dockerfile
    container_name: codelab-auth-service
    ports:
      - "${AUTH_SERVICE_PORT:-8003}:8003"
    volumes:
      - ./auth-service/data:/app/data
      - ./auth-service/keys:/app/keys
    environment:
      - ENVIRONMENT=${ENVIRONMENT:-development}
      - DEBUG=${DEBUG:-true}
      - PORT=8003
      - HOST=0.0.0.0
      - LOG_LEVEL=${LOG_LEVEL:-DEBUG}
      - AUTH_SERVICE__DB_URL=${AUTH_SERVICE__DB_URL:-sqlite:///data/auth.db}
      - AUTH_SERVICE__REDIS_URL=redis://redis:6379/1
      - AUTH_SERVICE__JWT_ISSUER=${AUTH_SERVICE__JWT_ISSUER:-https://auth.localhost}
      - AUTH_SERVICE__JWT_AUDIENCE=codelab-api
      - AUTH_SERVICE__REQUIRE_HTTPS=${AUTH_SERVICE__REQUIRE_HTTPS:-false}
      - AUTH_SERVICE__CORS_ORIGINS=${AUTH_SERVICE__CORS_ORIGINS:-*}
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - codelab-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: codelab-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - codelab-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  redis-data:

networks:
  codelab-network:
    driver: bridge
```

---

## 🔨 Конфигурация по окружениям

### Development окружение

**Файл: .env.development**

```bash
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

AUTH_SERVICE__DB_URL=sqlite:///data/auth.db
AUTH_SERVICE__REDIS_URL=redis://localhost:6379/0

AUTH_SERVICE__JWT_ISSUER=https://auth.localhost
AUTH_SERVICE__BCRYPT_ROUNDS=10
AUTH_SERVICE__RATE_LIMIT_IP_PER_MINUTE=100
AUTH_SERVICE__REQUIRE_HTTPS=false
AUTH_SERVICE__CORS_ORIGINS=http://localhost:3000,http://localhost:8000,http://localhost:8001
```

**Особенности:**
- SQLite БД (в памяти или файл)
- Отключен HTTPS
- Высокие rate limits (для тестирования)
- Verbose логирование
- CORS открыт для localhost

### Staging окружение

**Файл: .env.staging**

```bash
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO

AUTH_SERVICE__DB_URL=postgresql://user:pass@pg-staging:5432/auth_db
AUTH_SERVICE__REDIS_URL=redis://redis-staging:6379/0

AUTH_SERVICE__JWT_ISSUER=https://auth-staging.codelab.local
AUTH_SERVICE__BCRYPT_ROUNDS=12
AUTH_SERVICE__RATE_LIMIT_IP_PER_MINUTE=5
AUTH_SERVICE__REQUIRE_HTTPS=true
AUTH_SERVICE__CORS_ORIGINS=https://staging.codelab.local
```

**Особенности:**
- PostgreSQL БД
- HTTPS включен
- Стандартные rate limits
- Ограниченный CORS
- Обычное логирование

### Production окружение

**Файл: .env.production**

```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

AUTH_SERVICE__DB_URL=postgresql://user:secure_pass@pg-prod:5432/auth_db
AUTH_SERVICE__REDIS_URL=redis://redis-cluster:6379/0

AUTH_SERVICE__JWT_ISSUER=https://auth.codelab.local
AUTH_SERVICE__BCRYPT_ROUNDS=12
AUTH_SERVICE__RATE_LIMIT_IP_PER_MINUTE=5
AUTH_SERVICE__REQUIRE_HTTPS=true
AUTH_SERVICE__CORS_ORIGINS=https://app.codelab.local
AUTH_SERVICE__SENTRY_DSN=https://xxxxx@sentry.io/12345
AUTH_SERVICE__PRIVATE_KEY_PATH=/vault/keys/prod/private_key.pem
```

**Особенности:**
- PostgreSQL на production кластере
- HTTPS обязателен
- Strict rate limiting
- Minimal логирование
- Sentry для error tracking
- Ключи из vault/secure storage
- Health checks enabled
- Automatic scaling

---

## 🔑 Управление ключами

### Генерация RSA ключей

```bash
# Использовать встроенный скрипт
python scripts/generate_keys.py \
  --output-dir ./keys \
  --bits 2048 \
  --key-id 2024-01-key-1
```

**Результат:**
```
keys/
├── private_key.pem      # Приватный ключ (KEEP SECURE!)
├── public_key.pem       # Публичный ключ
└── public_key.json      # JWKS формат
```

### Хранение ключей

**Development:**
```bash
# В папке проекта
./keys/private_key.pem
./keys/public_key.pem
```

**Production:**
```bash
# В защищённом хранилище
/vault/keys/prod/private_key.pem
/vault/keys/prod/public_key.pem

# Или через переменные окружения
export AUTH_SERVICE__PRIVATE_KEY_PATH=/path/to/secure/private_key.pem
```

### Ротация ключей

```bash
# 1. Сгенерировать новый ключ
python scripts/generate_keys.py --key-id 2024-02-key-1

# 2. Обновить конфигурацию
AUTH_SERVICE__PRIVATE_KEY_PATH=/app/keys/2024-02-key-1/private_key.pem

# 3. Рестартовать сервис
docker-compose restart auth-service

# 4. Проверить JWKS (должны быть оба ключа)
curl http://localhost:8003/.well-known/jwks.json
```

---

## 🧪 Проверка конфигурации

### Health Check

```bash
# Проверить конфигурацию и зависимости
curl http://localhost:8003/health

# Ответ (все OK)
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-03-22T05:40:00.000Z",
  "checks": {
    "database": "connected",
    "redis": "connected"
  }
}

# Ответ (есть проблемы)
{
  "status": "degraded",
  "version": "1.0.0",
  "checks": {
    "database": "disconnected",
    "redis": "connected"
  }
}
```

### Validation скрипт

```bash
# Проверить все переменные окружения
python scripts/validate_config.py

# Вывод
✅ ENVIRONMENT: production
✅ AUTH_SERVICE__DB_URL: postgresql://...
✅ AUTH_SERVICE__REDIS_URL: redis://...
✅ AUTH_SERVICE__PRIVATE_KEY_PATH: /vault/keys/prod/private_key.pem
✅ Keys loaded successfully
✅ All validations passed!
```

---

## 📊 Примеры конфигураций

### Минимальная конфигурация (для тестирования)

```bash
# Все остальные значения используют defaults
ENVIRONMENT=development
AUTH_SERVICE__REDIS_URL=redis://localhost:6379/0
```

### Полная конфигурация (production)

```bash
# Базовое
ENVIRONMENT=production
DEBUG=false
PORT=8003
HOST=0.0.0.0
LOG_LEVEL=WARNING
WORKERS=8

# База данных
AUTH_SERVICE__DB_URL=postgresql://auth_user:secure_pass@pg-primary.internal:5432/codelab_auth
AUTH_SERVICE__DB_ECHO=false
AUTH_SERVICE__DB_POOL_SIZE=20
AUTH_SERVICE__DB_MAX_OVERFLOW=40
AUTH_SERVICE__DB_POOL_RECYCLE=3600

# Redis (Cluster)
AUTH_SERVICE__REDIS_URL=redis://redis-cluster.internal:6379/0
AUTH_SERVICE__REDIS_TIMEOUT=5
AUTH_SERVICE__REDIS_DB=0

# JWT
AUTH_SERVICE__JWT_ISSUER=https://auth.codelab.local
AUTH_SERVICE__JWT_AUDIENCE=codelab-api
AUTH_SERVICE__ACCESS_TOKEN_LIFETIME=900
AUTH_SERVICE__REFRESH_TOKEN_LIFETIME=2592000
AUTH_SERVICE__PRIVATE_KEY_PATH=/vault/keys/prod/2024-01-key-1/private_key.pem
AUTH_SERVICE__PUBLIC_KEY_PATH=/vault/keys/prod/2024-01-key-1/public_key.pem

# Безопасность
AUTH_SERVICE__BCRYPT_ROUNDS=12
AUTH_SERVICE__PASSWORD_MIN_LENGTH=8
AUTH_SERVICE__RATE_LIMIT_IP_PER_MINUTE=5
AUTH_SERVICE__RATE_LIMIT_USERNAME_PER_HOUR=10
AUTH_SERVICE__BRUTE_FORCE_THRESHOLD=5
AUTH_SERVICE__BRUTE_FORCE_LOCKOUT_MINUTES=15
AUTH_SERVICE__REQUIRE_HTTPS=true
AUTH_SERVICE__CORS_ORIGINS=https://app.codelab.local

# Логирование
AUTH_SERVICE__LOG_FORMAT=json
AUTH_SERVICE__SENTRY_DSN=https://key@sentry.codelab.local/123
```

---

## 🔍 Troubleshooting конфигурации

### Проблема: "Cannot connect to Redis"

**Решение:**
```bash
# Проверить URL
echo $AUTH_SERVICE__REDIS_URL  # redis://localhost:6379/0

# Проверить соединение
redis-cli -u redis://localhost:6379/0 ping

# Обновить конфигурацию
AUTH_SERVICE__REDIS_URL=redis://redis:6379/0  # Для Docker Compose
docker-compose restart auth-service
```

### Проблема: "Cannot load private key"

**Решение:**
```bash
# Проверить путь
echo $AUTH_SERVICE__PRIVATE_KEY_PATH  # /app/keys/private_key.pem

# Проверить существование файла
ls -la /app/keys/private_key.pem

# Проверить разрешения
chmod 400 /app/keys/private_key.pem

# Сгенерировать новый ключ
python scripts/generate_keys.py --output-dir ./keys
```

### Проблема: "Invalid CORS configuration"

**Решение:**
```bash
# Корректный формат (comma-separated, no spaces)
AUTH_SERVICE__CORS_ORIGINS=https://app.codelab.local,https://admin.codelab.local

# Проверить валидность
curl -H "Origin: https://app.codelab.local" http://localhost:8003/health
```

### Проблема: "Database migration failed"

**Решение:**
```bash
# Проверить connection string
echo $AUTH_SERVICE__DB_URL

# Проверить доступность БД
pg_isready -h pg-host -p 5432  # Для PostgreSQL

# Запустить миграции вручную
docker-compose exec auth-service alembic upgrade head

# Откатить на предыдущую версию
docker-compose exec auth-service alembic downgrade -1
```

---

## 📊 Performance Tuning

### Для высокой нагрузки

```bash
# Увеличить worker процессы
WORKERS=16

# Увеличить pool размер
AUTH_SERVICE__DB_POOL_SIZE=50
AUTH_SERVICE__DB_MAX_OVERFLOW=100

# Увеличить Redis pipeline
AUTH_SERVICE__REDIS_TIMEOUT=10

# Снизить bcrypt rounds (при необходимости)
AUTH_SERVICE__BCRYPT_ROUNDS=10  # вместо 12

# Снизить rate limits
AUTH_SERVICE__RATE_LIMIT_IP_PER_MINUTE=50
```

### Для низкой нагрузки (staging/demo)

```bash
# Минимум worker процессов
WORKERS=1

# Маленький pool
AUTH_SERVICE__DB_POOL_SIZE=2
AUTH_SERVICE__DB_MAX_OVERFLOW=5

# Высокие rate limits (для тестирования)
AUTH_SERVICE__RATE_LIMIT_IP_PER_MINUTE=100
AUTH_SERVICE__RATE_LIMIT_USERNAME_PER_HOUR=100
```

---

## 📞 Контакты

**Разработчик:** Sergey Penkovsky  
**Email:** sergey.penkovsky@gmail.com  
**Версия:** 1.0.0  
**Дата:** 2026-03-22
