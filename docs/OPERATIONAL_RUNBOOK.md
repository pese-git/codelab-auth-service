# Operational Runbook: User Sync и Token Blacklist

## Содержание

1. [Обзор системы](#обзор-системы)
2. [Переменные окружения](#переменные-окружения)
3. [Запуск и остановка сервиса](#запуск-и-остановка-сервиса)
4. [Мониторинг](#мониторинг)
5. [Troubleshooting](#troubleshooting)
6. [Emergency Procedures](#emergency-procedures)
7. [Maintenance Tasks](#maintenance-tasks)

---

## Обзор системы

### Архитектура

```
Auth Service                              Core Service
┌─────────────────────┐                  ┌──────────────────┐
│  User Management    │                  │  User Profiles   │
│  Token Management   │                  │  User Isolation  │
└──────────┬──────────┘                  └────────┬─────────┘
           │                                      ▲
           │ Публикует события                    │
           │ user.created                         │ Потребляет события
           │ user.updated                         │
           │ user.deleted                         │
           │ token.revoked                        │
           │                                      │
           └──────────────► Redis Streams ◄──────┘
                         (user_events)
                         (user_events_dlq)

           ┌─────────────────────┐
           │  Token Blacklist    │
           │  (Redis)            │
           └─────────────────────┘
                    ▲
                    │ Проверка
                    │
           ┌──────────────────────┐
           │  Core Service        │
           │  UserIsolationMiddleware
           └──────────────────────┘
```

### Критические компоненты

1. **Redis Streams** - буфер событий между сервисами
2. **Token Blacklist (Redis)** - хранилище отозванных токенов
3. **Event Consumer** - обработчик событий в Core Service
4. **User Event Handlers** - обработчики создания/обновления/удаления пользователей

---

## Переменные окружения

### Auth Service

```env
# Redis Streams Configuration
EVENTS_STREAM_KEY=user_events
EVENTS_STREAM_MAXLEN=100000
EVENTS_STREAM_MIN_CHUNK_SIZE=1000
EVENTS_VERSION=1.0
USE_EVENT_PUBLISHING=true

# Token Blacklist Configuration
USE_TOKEN_BLACKLIST=true
TOKEN_BLACKLIST_MIN_TTL=3600

# Redis Connection
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=redis-secure-password-change-in-production
REDIS_DB=0
```

### Core Service

```env
# Event Consumer Configuration
USE_EVENT_CONSUMER=true
EVENTS_STREAM_KEY=user_events
EVENTS_CONSUMER_GROUP=core_service_consumer_group
EVENTS_CONSUMER_NAME=core_service_consumer_1
EVENTS_BATCH_SIZE=10
EVENTS_CONSUMER_TIMEOUT=1000

# Event Processing
EVENTS_MAX_RETRIES=3
EVENTS_RETRY_BACKOFF_BASE=1
EVENTS_DLQ_STREAM_KEY=user_events_dlq
EVENTS_VERSION=1.0

# Token Blacklist
USE_TOKEN_BLACKLIST=true
TOKEN_BLACKLIST_MIN_TTL=3600
```

---

## Запуск и остановка сервиса

### 1. Запуск Development окружения

```bash
# Запуск всех сервисов
docker-compose up

# Или конкретных сервисов
docker-compose up redis postgres codelab-auth-service codelab-core-service

# В фоне
docker-compose up -d
```

### 2. Проверка статуса

```bash
# Проверка запущенных контейнеров
docker-compose ps

# Логи Auth Service
docker-compose logs -f codelab-auth-service

# Логи Core Service
docker-compose logs -f codelab-core-service

# Логи Redis
docker-compose logs -f redis
```

### 3. Остановка сервисов

```bash
# Остановка всех сервисов
docker-compose down

# Остановка конкретного сервиса
docker-compose stop codelab-auth-service

# Удаление томов (база данных)
docker-compose down -v
```

---

## Мониторинг

### 1. Проверка Redis Streams

```bash
# Подключение к Redis
redis-cli -h localhost -p 6379 -a redis-secure-password-change-in-production

# Получение информации о потоке user_events
> XINFO STREAM user_events

# Получение количества сообщений
> XLEN user_events

# Чтение последних 5 сообщений
> XREVRANGE user_events + COUNT 5

# Получение информации о группе потребителей
> XINFO GROUPS user_events

# Получение информации о потребителях в группе
> XINFO CONSUMERS user_events core_service_consumer_group

# Проверка DLQ потока
> XLEN user_events_dlq
> XREVRANGE user_events_dlq + COUNT 5
```

### 2. Проверка Token Blacklist

```bash
# Подключение к Redis
redis-cli -h localhost -p 6379 -a redis-secure-password-change-in-production

# Получение количества отозванных токенов
> DBSIZE

# Проверка конкретного токена
> GET blacklist:token:<jti>

# Получение всех токенов пользователя
> SMEMBERS user:tokens:<user_id>

# Проверка TTL токена
> TTL blacklist:token:<jti>
```

### 3. Проверка Database синхронизации

```bash
# Auth Service
psql -h localhost -U postgres -d codelab -c "
SELECT id, username, email, is_deleted, deleted_at, deletion_reason
FROM users
WHERE is_deleted = true
ORDER BY deleted_at DESC LIMIT 10;
"

# Core Service
psql -h localhost -U postgres -d codelab -c "
SELECT id, username, email, synced_from_auth_at, synced_version
FROM users
ORDER BY synced_from_auth_at DESC LIMIT 10;
"
```

### 4. Metrics (Prometheus)

```promql
# Auth Service Metrics

# События опубликованные в секунду
rate(auth_events_published_total[5m])

# P95 задержка публикации события
histogram_quantile(0.95, auth_event_publish_duration_seconds_bucket)

# Количество активных отозванных токенов
auth_active_blacklisted_tokens

# Размер потока
auth_event_stream_size
```

```promql
# Core Service Metrics

# События обработаны в секунду
rate(core_events_processed_total[5m])

# Задержка обработки события
histogram_quantile(0.95, core_event_processing_duration_seconds_bucket)

# Размер DLQ
core_events_dlq_total

# Задержка группы потребителей
core_consumer_group_lag
```

---

## Troubleshooting

### 1. Event Consumer не обрабатывает события

**Симптомы:**
- События публикуются, но не обрабатываются в Core Service
- Задержка группы потребителей растет
- Нет логов обработки в Core Service

**Диагностика:**

```bash
# 1. Проверить количество сообщений в потоке
redis-cli -h localhost -p 6379 XLEN user_events

# 2. Проверить информацию о группе потребителей
redis-cli -h localhost -p 6379 XINFO GROUPS user_events

# 3. Проверить логи Core Service на ошибки
docker-compose logs codelab-core-service | grep -i error

# 4. Проверить статус Redis
docker-compose exec redis redis-cli PING

# 5. Проверить базу данных Core Service
psql -h localhost -U postgres -d codelab -c "SELECT COUNT(*) FROM users;"
```

**Решение:**

```bash
# Вариант 1: Перезагрузить Core Service
docker-compose restart codelab-core-service

# Вариант 2: Воссоздать группу потребителей
redis-cli -h localhost -p 6379 XGROUP DESTROY user_events core_service_consumer_group
docker-compose restart codelab-core-service

# Вариант 3: Обработать pending сообщения
# Обработчик автоматически обработает их при запуске
```

### 2. Token Blacklist не работает

**Симптомы:**
- Отозванные токены все еще принимаются
- Middleware не блокирует запросы
- Redis недоступен

**Диагностика:**

```bash
# 1. Проверить Redis соединение
redis-cli -h localhost -p 6379 PING

# 2. Проверить логи Auth Service
docker-compose logs codelab-auth-service | grep -i "blacklist\|token"

# 3. Проверить наличие токена в blacklist
redis-cli -h localhost -p 6379 GET "blacklist:token:<jti>"

# 4. Проверить TTL токена
redis-cli -h localhost -p 6379 TTL "blacklist:token:<jti>"
```

**Решение:**

```bash
# Вариант 1: Перезагрузить Redis
docker-compose restart redis

# Вариант 2: Проверить конфигурацию Redis в .env
# USE_TOKEN_BLACKLIST=true
# TOKEN_BLACKLIST_MIN_TTL=3600

# Вариант 3: Вручную отозвать токены (если Redis восстановлен)
# Использовать API endpoint: DELETE /admin/users/{user_id}
```

### 3. DLQ переполнен

**Симптомы:**
- Есть сообщения в user_events_dlq
- Обработчики генерируют исключения
- Сообщения не обрабатываются

**Диагностика:**

```bash
# 1. Проверить размер DLQ
redis-cli -h localhost -p 6379 XLEN user_events_dlq

# 2. Прочитать первое сообщение из DLQ
redis-cli -h localhost -p 6379 XREAD COUNT 1 STREAMS user_events_dlq 0

# 3. Посмотреть логи ошибок Core Service
docker-compose logs codelab-core-service | tail -100
```

**Решение:**

```bash
# Вариант 1: Исправить ошибку обработчика и перезагрузить
docker-compose restart codelab-core-service

# Вариант 2: Вручную переместить сообщение из DLQ
# (требует разработки скрипта восстановления)

# Вариант 3: Очистить DLQ (если данные не важны)
redis-cli -h localhost -p 6379 DEL user_events_dlq
```

### 4. Database синхронизация потеряна

**Симптомы:**
- Пользователь есть в Auth Service, но не в Core Service
- Запросы к API падают с ошибкой изоляции пользователя
- Данные несинхронизированы

**Диагностика:**

```bash
# 1. Найти отсутствующих пользователей
psql -h localhost -U postgres -d codelab << EOF
-- Auth Service
SELECT DISTINCT a.id FROM codelab_auth.users a
LEFT JOIN codelab_core.users c ON a.id = c.id
WHERE c.id IS NULL;
EOF

# 2. Проверить последний синхронизированный пользователь
psql -h localhost -U postgres -d codelab -c "
SELECT * FROM users ORDER BY synced_from_auth_at DESC LIMIT 1;
"

# 3. Проверить события в потоке для этого пользователя
redis-cli -h localhost -p 6379 XREAD COUNT 100 STREAMS user_events 0
```

**Решение:**

```bash
# Вариант 1: Пересинхронизировать пользователей
# Требует разработки скрипта миграции

# Вариант 2: Вручную вставить пользователя в Core Service
psql -h localhost -U postgres -d codelab << EOF
INSERT INTO users (id, username, email, synced_from_auth_at, synced_version)
SELECT id, username, email, NOW(), '1.0'
FROM codelab_auth.users
WHERE id NOT IN (SELECT id FROM codelab_core.users);
EOF

# Вариант 3: Перезагрузить consumer с началом потока
redis-cli -h localhost -p 6379 XGROUP SETID user_events core_service_consumer_group 0
docker-compose restart codelab-core-service
```

---

## Emergency Procedures

### 1. Отключение Event Publishing (неэкстренная ситуация)

Если Redis Streams недоступны, но нужно продолжить работу:

```bash
# 1. Отключить публикацию событий в Auth Service
# Обновить .env:
USE_EVENT_PUBLISHING=false

# 2. Перезагрузить Auth Service
docker-compose restart codelab-auth-service

# 3. Примечание: Core Service не будет синхронизирован до восстановления
```

### 2. Отключение Token Blacklist (критическая ситуация)

Если Redis недоступен для token blacklist, но нужны операции Auth Service:

```bash
# 1. Отключить blacklist проверки в Auth Service
# Обновить .env:
USE_TOKEN_BLACKLIST=false

# 2. Перезагрузить Auth Service
docker-compose restart codelab-auth-service

# ⚠️ ВНИМАНИЕ: Отозванные токены будут приниматься!
# Используйте только в критических ситуациях
```

### 3. Восстановление после полного сбоя Redis

```bash
# 1. Очистить Redis
docker-compose exec redis redis-cli FLUSHALL

# 2. Пересоздать группу потребителей
docker-compose exec redis redis-cli XGROUP CREATE user_events core_service_consumer_group 0

# 3. Пересинхронизировать всех пользователей
# Требует скрипта миграции или повторной регистрации

# 4. Перезагрузить оба сервиса
docker-compose restart codelab-auth-service codelab-core-service
```

### 4. Откат удаления пользователя

Если пользователь был удален ошибочно:

```bash
# 1. Остановить Core Service (чтобы избежать дальнейших изменений)
docker-compose stop codelab-core-service

# 2. Восстановить пользователя в Auth Service (soft delete)
psql -h localhost -U postgres -d codelab << EOF
UPDATE users SET is_deleted = false, deleted_at = NULL
WHERE id = '<user_id>';
EOF

# 3. Восстановить пользователя в Core Service
psql -h localhost -U postgres -d codelab << EOF
INSERT INTO users (id, username, email, synced_from_auth_at)
VALUES ('<user_id>', '<username>', '<email>', NOW())
ON CONFLICT DO NOTHING;
EOF

# 4. Очистить события удаления из потока (если нужно)
# Требует разработки скрипта очистки

# 5. Перезагрузить Core Service
docker-compose start codelab-core-service
```

---

## Maintenance Tasks

### 1. Ежедневное обслуживание

```bash
# Проверка логов на ошибки
docker-compose logs --since 24h | grep -i "error\|exception\|failed"

# Проверка размера потоков Redis
redis-cli -h localhost -p 6379 << EOF
XLEN user_events
XLEN user_events_dlq
EOF

# Проверка задержки потребителей
redis-cli -h localhost -p 6379 XINFO GROUPS user_events
```

### 2. Еженедельное обслуживание

```bash
# Очистка старых событий (если есть архивирование)
# Требует разработки скрипта архивирования

# Проверка состояния базы данных
docker-compose exec postgres pg_dump codelab | gzip > backup_$(date +%Y%m%d).sql.gz

# Анализ метрик Prometheus
# Проверить тренды задержек и объемов
```

### 3. Ежемесячное обслуживание

```bash
# Обновление конфигурации Redis Stream MAXLEN
# Проверить, адекватны ли текущие лимиты

# Проверка и очистка Dead Letter Queue
redis-cli -h localhost -p 6379 XLEN user_events_dlq

# Если DLQ растет, требуется анализ причин

# Обновление политик сохранения токенов
# Проверить TOKEN_BLACKLIST_MIN_TTL в зависимости от трафика

# Проверка резервных копий
ls -lh backup_*.sql.gz
```

### 4. Операции масштабирования

```bash
# Увеличение MAXLEN потока
# Обновить в .env:
EVENTS_STREAM_MAXLEN=200000  # с 100000

# Увеличение размера batch обработки
EVENTS_BATCH_SIZE=20  # с 10

# Запуск дополнительного потребителя (если микросервис несколько)
# EVENTS_CONSUMER_NAME=core_service_consumer_2
```

---

## Контакты и эскалация

### Уровень 1: Проверить логи

Самые частые проблемы находятся в логах:

```bash
docker-compose logs | grep -i error
```

### Уровень 2: Перезагрузка

Для большинства проблем помогает перезагрузка:

```bash
docker-compose restart
```

### Уровень 3: Инженер-разработчик

- Проверить исходный код обработчиков
- Анализ базы данных и Redis состояния
- Разработка скриптов восстановления

### Уровень 4: DevOps/SRE

- Масштабирование инфраструктуры
- Восстановление резервных копий
- Миграция данных

---

## Полезные команды

```bash
# Быстрая диагностика
docker-compose ps
docker-compose logs --tail=50
redis-cli PING
psql -c "SELECT 1"

# Очистка (⚠️ осторожно!)
docker-compose down -v  # Удалить все данные
docker system prune -a  # Удалить неиспользуемые ресурсы

# Восстановление
docker-compose up -d
docker-compose exec postgres psql -c "CREATE DATABASE codelab;"
```
