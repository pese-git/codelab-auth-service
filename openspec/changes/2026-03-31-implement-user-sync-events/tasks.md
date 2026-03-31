# Tasks: Event-Driven синхронизация и Token Blacklist (Auth Service)

**Версия:** 1.0.0  
**Дата:** 31 марта 2026  
**Приоритет:** High

---

## 📋 Список задач по приоритетам

### 🔴 Phase 1: Foundation (Must Have)

#### Task 1.1: Создать TokenBlacklistService
- **Описание:** Реализовать сервис управления blacklist токенов
- **Файлы:**
  - `app/services/token_blacklist_service.py` — основной класс
  - `tests/test_token_blacklist_service.py` — unit тесты
- **Зависимости:** Redis client (уже есть)
- **Критерии приёмки:**
  - ✅ `revoke_token()` сохраняет токен в Redis с TTL
  - ✅ `revoke_all_user_tokens()` отзывает batch токенов
  - ✅ `is_token_revoked()` проверяет наличие в blacklist
  - ✅ Метаданные сохраняются (причина, админ, время)
  - ✅ TTL корректно вычисляется (exp - now, мин 3600s)
  - ✅ Unit тесты: 100% coverage для TokenBlacklistService
- **Ответственный:** Backend Dev

#### Task 1.2: Создать EventPublisher для Redis Streams
- **Описание:** Реализовать издатель событий в Redis Streams
- **Файлы:**
  - `app/services/event_publisher.py` — publisher класс
  - `app/schemas/event.py` — event data models
  - `tests/test_event_publisher.py` — unit тесты
- **Зависимости:** Redis client, Task 1.1
- **Критерии приёмки:**
  - ✅ `publish_event()` добавляет событие в stream
  - ✅ Event envelope правильный формат (event_id, timestamp, etc.)
  - ✅ XADD работает с MAXLEN pruning
  - ✅ Correlation ID поддерживается
  - ✅ Ошибки логируются, не падает
  - ✅ Unit тесты: 100% coverage
- **Ответственный:** Backend Dev

#### Task 1.3: Обновить User Deletion Flow
- **Описание:** Интегрировать blacklist revoke + event publish в процесс удаления
- **Файлы:**
  - `app/services/user_service.py` — обновить `delete_user()`
  - `app/api/v1/admin.py` — обновить endpoint
  - `tests/test_user_deletion_flow.py` — integration тесты
- **Зависимости:** Task 1.1, Task 1.2
- **Критерии приёмки:**
  - ✅ При DELETE user: получить все active tokens
  - ✅ Отозвать все токены в blacklist (batch)
  - ✅ Обновить БД (is_deleted=true)
  - ✅ Опубликовать `user.deleted` событие
  - ✅ Transaction ACID (все или ничего)
  - ✅ Логирование каждого шага
  - ✅ Integration тесты (end-to-end flow)
- **Ответственный:** Backend Dev

#### Task 1.4: Добавить Database Schema Migration
- **Описание:** Alembic миграция для колонок удаления пользователя
- **Файлы:**
  - `migrations/versions/2026_03_31_add_user_deletion_fields.py`
- **Зависимости:** Task 1.3
- **Критерии приёмки:**
  - ✅ Миграция создает is_deleted, deleted_at, deletion_reason колонки
  - ✅ Миграция добавляет индекс на (is_deleted, deleted_at)
  - ✅ Downgrade работает корректно
  - ✅ Тесть миграция на clean DB
- **Ответственный:** Backend Dev / DevOps

---

### 🟡 Phase 2: Integration & Testing

#### Task 2.1: Написать Unit Tests для TokenBlacklistService
- **Описание:** Полное покрытие unit тестами
- **Тесты должны покрывать:**
  - ✅ Успешный revoke одного токена
  - ✅ Успешный revoke всех токенов
  - ✅ Проверка что токен в blacklist
  - ✅ TTL автоматически очищает expired токены
  - ✅ Метаданные сохраняются и читаются
  - ✅ Error handling (Redis connection error)
  - ✅ Edge cases (токен уже истек, пустой список)
- **Критерии приёмки:**
  - ✅ Coverage >= 95%
  - ✅ Все тесты проходят
  - ✅ Тесты запускаются с pytest
- **Ответственный:** QA / Backend Dev

#### Task 2.2: Написать Integration Tests для Event Publishing
- **Описание:** E2E тесты для события → redis stream
- **Тесты должны покрывать:**
  - ✅ Event публикуется в stream
  - ✅ Message ID возвращается
  - ✅ Event payload правильный формат
  - ✅ Несколько событий одновременно (concurrent publish)
  - ✅ MAXLEN pruning работает
- **Критерии приёмки:**
  - ✅ Все тесты зелёные
  - ✅ Можно читать события из stream вручную (redis-cli)
- **Ответственный:** QA

#### Task 2.3: Написать E2E тест User Deletion Flow
- **Описание:** Полный сценарий: DELETE user → blacklist → event → DLQ
- **Сценарий:**
  1. Создать пользователя с token
  2. Проверить token активен
  3. Удалить пользователя
  4. Проверить token в blacklist
  5. Проверить event опубликован в stream
- **Критерии приёмки:**
  - ✅ Тест проходит
  - ✅ Все ассерты зелёные
  - ✅ Логирование показывает правильный flow
- **Ответственный:** QA

#### Task 2.4: Обновить .env и Configuration
- **Описание:** Добавить env vars для Redis Streams, Token Blacklist
- **Файлы:**
  - `.env.example` — обновить с новыми vars
  - `app/config.py` — добавить настройки
  - `.env.production.example` — production defaults
- **Зависимости:** Task 1.2, Task 1.3
- **Критерии приёмки:**
  - ✅ Все требуемые env vars определены
  - ✅ Defaults reasonable
  - ✅ Конфиг загружается без ошибок
  - ✅ Документировано в README
- **Ответственный:** DevOps

---

### 🟢 Phase 3: Optimization & Documentation

#### Task 3.1: Добавить Monitoring & Logging
- **Описание:** Метрики для мониторинга blacklist, event publisher
- **Метрики:**
  - `tokens_revoked_total` — счетчик отозванных токенов
  - `blacklist_check_duration_seconds` — latency проверки
  - `events_published_total` — счетчик опубликованных событий
  - `event_publish_duration_seconds` — latency публикации
  - `redis_connection_errors` — счетчик ошибок Redis
- **Файлы:**
  - `app/metrics/blacklist_metrics.py` — metrics регистрация
  - `app/metrics/event_metrics.py` — event metrics
- **Критерии приёмки:**
  - ✅ Prometheus metrics expose на /metrics
  - ✅ Метрики обновляются при revoke/publish
  - ✅ Alerts сконфигурированы в prometheus.yml
- **Ответственный:** DevOps

#### Task 3.2: Написать API Documentation
- **Описание:** OpenAPI документация для новых endpoints
- **Файлы:**
  - `docs/api/token-blacklist.md` — Token Blacklist API
  - `docs/api/event-publisher.md` — Event Publisher API
  - `docs/api/user-deletion.md` — User Deletion Flow
- **Содержание:**
  - Request/Response examples
  - Error codes
  - Rate limiting info
  - Retry strategy
- **Критерии приёмки:**
  - ✅ Документация полная
  - ✅ Примеры работают
  - ✅ Swagger docs обновлены
- **Ответственный:** Tech Writer / Backend Dev

#### Task 3.3: Написать Operational Runbook
- **Описание:** Гайд для операций: мониторинг, troubleshooting
- **Файлы:**
  - `docs/operational/token-blacklist-runbook.md`
  - `docs/operational/event-publisher-runbook.md`
- **Содержание:**
  - Health checks
  - Common issues and fixes
  - Redis CLI commands
  - Escalation path
  - Metrics to monitor
- **Критерии приёмки:**
  - ✅ Документация полная
  - ✅ Команды протестированы
- **Ответственный:** DevOps

#### Task 3.4: Graceful Degradation Implementation
- **Описание:** Fallback поведение если Redis недоступен
- **Компоненты:**
  - TokenBlacklistService — rely on exp claim только
  - EventPublisher — логировать и продолжать (не падать)
  - Admin API — не блокировать deletion если Redis down
- **Файлы:**
  - `app/services/token_blacklist_service.py` — update
  - `app/services/event_publisher.py` — update
- **Критерии приёмки:**
  - ✅ При Redis connection error: graceful fallback
  - ✅ Alerts отправляются в мониторинг
  - ✅ Deletion не падает
  - ✅ Логирование точное для debug'инга
- **Ответственный:** Backend Dev

---

## 📊 Dependencies Graph

```
Task 1.1: TokenBlacklistService
    ↓
Task 1.2: EventPublisher
    ↓
Task 1.3: User Deletion Flow
    ├─→ Task 1.4: Database Migration
    │
    ├─→ Task 2.1: Unit Tests (TokenBlacklist)
    ├─→ Task 2.2: Integration Tests (Events)
    ├─→ Task 2.3: E2E Tests (Deletion Flow)
    │
    └─→ Task 2.4: Configuration & ENV
        ↓
    Task 3.1: Monitoring
    Task 3.2: API Documentation
    Task 3.3: Operational Runbook
    Task 3.4: Graceful Degradation
```

---

## ⏱️ Estimation (без привязки к временным метрикам)

| Task | Complexity | Effort | Dependencies |
|------|-----------|--------|--------------|
| 1.1 | Low | Small | Redis client |
| 1.2 | Medium | Medium | Redis, 1.1 |
| 1.3 | High | Large | 1.1, 1.2, Database |
| 1.4 | Low | Small | 1.3 |
| 2.1 | Low | Small | 1.1 |
| 2.2 | Medium | Medium | 1.2 |
| 2.3 | High | Large | 1.3, 2.1, 2.2 |
| 2.4 | Low | Small | 1.2, 1.3 |
| 3.1 | Medium | Medium | 1.1, 1.2 |
| 3.2 | Low | Small | All Phase 1,2 |
| 3.3 | Low | Small | All Phase 1,2 |
| 3.4 | Medium | Medium | 1.1, 1.2, 1.3 |

---

## 🎯 Success Criteria (все Phase)

- ✅ Все задачи completed
- ✅ Unit tests: 95%+ coverage
- ✅ Integration tests: все зелёные
- ✅ E2E tests: все сценарии passed
- ✅ Documentation: complete и up-to-date
- ✅ Code review: approved
- ✅ No production incidents related to these changes
- ✅ Metrics monitoring: alerts working
- ✅ Performance: token revocation < 100ms p95
- ✅ Reliability: event delivery > 99.9%
