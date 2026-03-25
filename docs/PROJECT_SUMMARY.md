# Резюме проекта Auth Service

**Версия:** 1.1.0
**Дата:** 25 марта 2026
**Статус:** ✅ Реализовано (с Email Integration)

---

## Обзор

Auth Service — микросервис аутентификации и авторизации для платформы CodeLab, реализующий OAuth2 Authorization Server с поддержкой Password Grant и Refresh Token Grant, а также SMTP интеграцией для отправки email уведомлений при регистрации и важных событиях в системе.

---

## Созданные документы

### 1. [Техническое задание](TECHNICAL_SPECIFICATION.md)
**Объем:** ~1500 строк  
**Содержание:**
- Полное описание требований к Auth Service
- OAuth2 спецификация (Password Grant, Refresh Token Grant)
- JWT токены (Access и Refresh)
- Модель данных (Users, OAuth Clients, Refresh Tokens, Audit Logs)
- API контракты с примерами
- Требования безопасности
- Интеграция с существующими сервисами (Gateway, Agent Runtime, LLM Proxy)
- Нефункциональные требования (производительность, масштабирование)

**Ключевые решения:**
- ✅ SQLite вместо PostgreSQL (для упрощения развертывания)
- ✅ RS256 для JWT (асимметричная криптография)
- ✅ Refresh token rotation (одноразовые токены)
- ✅ Stateless access tokens (не хранятся в БД)
- ✅ Redis для кэширования и rate limiting

### 2. [План реализации](IMPLEMENTATION_PLAN.md)
**Объем:** ~800 строк  
**Содержание:**
- 12 итераций разработки
- Детальные задачи для каждой итерации
- Критерии приемки
- Оценка времени
- Риски и митигация
- Зависимости между итерациями

**Итерации:**
1. Подготовка инфраструктуры (1-2 дня)
2. Модели данных и миграции (2-3 дня)
3. Криптография и безопасность (2-3 дня)
4. User Service и аутентификация (2-3 дня)
5. OAuth2 Password Grant (3-4 дня)
6. Rate Limiting и защита (2-3 дня)
7. Аудит и логирование (1-2 дня)
8. Интеграция с Gateway (2-3 дня)
9. Интеграция с Agent Runtime (1-2 дня)
10. Документация и примеры (2-3 дня)
11. Тестирование и оптимизация (3-4 дня)
12. Мониторинг и observability (2-3 дня)
13. Финализация и деплой (2-3 дня)

### 3. [Интеграционные точки](INTEGRATION_POINTS.md)
**Объем:** ~600 строк  
**Содержание:**
- Детальное описание интеграции с Gateway
- Детальное описание интеграции с Agent Runtime
- Детальное описание интеграции с LLM Proxy
- Docker Compose конфигурация
- Последовательность миграции (6 этапов)
- Обратная совместимость (гибридный middleware)
- Тестирование интеграции
- Мониторинг интеграции
- Rollback план

**Ключевые моменты:**
- Переходный период с поддержкой старой аутентификации
- JWT Auth Middleware для всех сервисов
- Кэширование JWKS
- Извлечение user_id из токенов

### 4. [README](../README.md)
**Объем:** ~500+ строк  
**Содержание:**
- Быстрый старт
- API endpoints с примерами
- Email Notifications секция (новое)
- Структура проекта
- Руководство по разработке
- Конфигурация SMTP
- Безопасность
- Мониторинг
- Тестирование
- Troubleshooting
- Roadmap

### 5. [Email Setup Guide](EMAIL_SETUP.md) ✨ НОВОЕ
**Объем:** ~400+ строк  
**Содержание:**
- Инструкции по настройке SMTP для различных провайдеров
- SendGrid, AWS SES, Mailgun конфигурация
- MailHog для локальной разработки
- Примеры `.env` файлов
- Troubleshooting guide для email проблем

### 6. [Integration Tests Documentation](INTEGRATION_TESTS.md) ✨ НОВОЕ
**Объем:** ~300+ строк  
**Содержание:**
- Инструкции по запуску integration тестов
- Тестирование email отправки
- MailHog использование в тестах
- Примеры тестовых сценариев

### 7. [QA Report - SMTP Integration](QA_REPORT_SMTP.md) ✨ НОВОЕ
**Объем:** ~500+ строк  
**Содержание:**
- Результаты QA тестирования (Phases 9-10)
- 84 тестов: 70 unit + 14 integration
- Coverage: 85%
- Тестовые сценарии и результаты
- Обнаруженные баги и их разрешение

---

## Архитектурные решения

### Технологический стек

| Компонент | Решение | Обоснование |
|-----------|---------|-------------|
| Язык | Python 3.12 | Соответствие существующим сервисам |
| Framework | FastAPI | Используется во всех сервисах CodeLab |
| БД | SQLite → PostgreSQL | Простота для MVP, миграция для production |
| Cache | Redis | Rate limiting, кэширование JWKS |
| JWT | RS256 (RSA 2048) | Асимметричная криптография для распределенной валидации |
| Password | bcrypt (cost 12) | Стандарт индустрии |
| ORM | SQLAlchemy | Поддержка миграций, абстракция БД |
| Миграции | Alembic | Стандарт для SQLAlchemy |

### OAuth2 Grant Types

**MVP:**
- ✅ Password Grant — для Flutter клиента
- ✅ Refresh Token Grant — для обновления токенов

**Post-MVP:**
- ⏳ Authorization Code Flow + PKCE — для веб-приложений
- ⏳ Client Credentials — для межсервисного взаимодействия

### JWT Токены

**Access Token:**
- Время жизни: 15 минут
- Алгоритм: RS256
- Хранение: НЕ хранится (stateless)
- Размер: ~500-800 байт

**Refresh Token:**
- Время жизни: 30 дней
- Алгоритм: RS256
- Хранение: в БД (хэш jti)
- Одноразовый: rotation при использовании

### Безопасность

**Защита:**
- ✅ Rate limiting (5/min на IP, 10/hour на username)
- ✅ Brute-force защита (блокировка после 5 попыток)
- ✅ Refresh token reuse detection
- ✅ HTTPS only
- ✅ Constant-time password comparison

**Валидация:**
- ✅ Email формат
- ✅ Пароль сложность (8+ символов, заглавные, цифры, спецсимволы)
- ✅ Scope валидация
- ✅ Grant type валидация

---

## Модель данных

### Таблицы

1. **users** — пользователи системы
   - id (UUID), username, email, password_hash
   - is_active, is_verified
   - created_at, updated_at, last_login_at

2. **oauth_clients** — OAuth клиенты
   - id (UUID), client_id, client_secret_hash
   - allowed_scopes, allowed_grant_types
   - access_token_lifetime, refresh_token_lifetime

3. **refresh_tokens** — refresh токены
   - id (UUID), jti_hash, user_id, client_id
   - scope, expires_at, revoked
   - parent_jti_hash (для rotation chain)

4. **audit_logs** — аудит логи (опционально)
   - id (UUID), user_id, client_id, event_type
   - event_data (JSONB), ip_address, user_agent
   - success, error_message

### Индексы

- users: email, username, is_active
- oauth_clients: client_id, is_active
- refresh_tokens: jti_hash, user_id, expires_at, revoked
- audit_logs: user_id, event_type, created_at, success

---

## API Endpoints

### POST /oauth/token
**Назначение:** Выдача и обновление токенов

**Grant Types:**
- `password` — аутентификация по login/password
- `refresh_token` — обновление access token

**Параметры:**
- grant_type (required)
- username, password (для password grant)
- refresh_token (для refresh_token grant)
- client_id (required)
- scope (optional)

**Ответ:**
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 900,
  "scope": "api:read api:write"
}
```

### GET /.well-known/jwks.json
**Назначение:** Публичные ключи для валидации JWT

**Ответ:**
```json
{
  "keys": [
    {
      "kty": "RSA",
      "use": "sig",
      "kid": "2024-01-key-1",
      "alg": "RS256",
      "n": "...",
      "e": "AQAB"
    }
  ]
}
```

### GET /health
**Назначение:** Health check

**Ответ:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "connected",
  "redis": "connected"
}
```

---

## Интеграция с существующими сервисами

### Gateway

**Изменения:**
1. Добавить `python-jose[cryptography]`
2. Создать `JWTAuthMiddleware`
3. Получать JWKS от Auth Service
4. Валидировать JWT токены
5. Извлекать user_id и scope

**Переходный период:**
- Поддержка JWT и X-Internal-Auth одновременно
- Постепенная миграция клиентов
- Мониторинг обоих методов

### Agent Runtime

**Изменения:**
1. Добавить `JWTAuthMiddleware`
2. Добавить `user_id` в модели сессий
3. Создать миграцию БД
4. Привязать сессии к пользователям

### LLM Proxy

**Решение:**
- Оставить внутреннюю аутентификацию (X-Internal-Auth)
- Используется только внутренними сервисами
- Опционально: добавить JWT для прямого доступа

---

## Последовательность миграции

### Этап 1: Развертывание Auth Service (неделя 1-2)
- Развернуть Auth Service
- Создать тестовых пользователей
- Протестировать OAuth2 flow

### Этап 2: Интеграция с Gateway (неделя 3)
- Добавить JWTAuthMiddleware
- Переходный период (оба метода)
- Тестирование

### Этап 3: Обновление Flutter клиента (неделя 4)
- Реализовать OAuth2 flow
- Хранение токенов
- Автообновление

### Этап 4: Переключение Gateway на JWT (неделя 5)
- Включить JWT аутентификацию
- Мониторинг
- Откат при проблемах

### Этап 5: Интеграция с Agent Runtime (неделя 6)
- Добавить JWTAuthMiddleware
- Обновить модели
- Миграция БД

### Этап 6: Удаление старой аутентификации (неделя 7-8)
- Убедиться в миграции всех клиентов
- Удалить InternalAuthMiddleware
- Финальное тестирование

---

## Производительность

### Требования
- ⚡ Время ответа `/oauth/token` < 200ms (p95)
- ⚡ Throughput: 100 RPS на инстанс
- ⚡ Latency JWKS endpoint < 50ms
- 🛡️ Доступность: 99.9%

### Оптимизация
- JWKS кэшируется в Redis (TTL 1 час)
- OAuth clients кэшируются (TTL 5 минут)
- SQLite в WAL режиме
- Connection pooling
- Индексы на часто используемые поля

### Масштабирование
- Stateless access tokens
- Горизонтальное масштабирование
- Общая БД для refresh tokens
- Redis для rate limiting

---

## Тестирование

### Coverage
- Требование: > 80%
- Unit тесты для всех сервисов
- Integration тесты для OAuth2 flow
- Security тесты
- Performance тесты

### Типы тестов
1. **Unit тесты** — сервисы, утилиты, middleware
2. **Integration тесты** — полный OAuth2 flow
3. **Security тесты** — SQL injection, JWT tampering, brute-force
4. **Performance тесты** — load testing, latency benchmarks

---

## Мониторинг

### Prometheus метрики
- `auth_token_requests_total` — количество запросов
- `auth_token_request_duration_seconds` — время обработки
- `auth_failed_login_attempts_total` — неудачные попытки
- `auth_refresh_token_rotations_total` — ротации токенов

### Логирование
- Structured logs (JSON)
- Correlation ID
- События: login, token_refresh, token_revoke
- Без паролей и токенов в логах

### Alerting
- Высокий процент неудачных входов
- Медленные запросы (> 200ms)
- Проблемы с БД или Redis
- Обнаружение refresh token reuse

---

## Риски и митигация

### Риск 1: Производительность SQLite
**Вероятность:** Средняя  
**Влияние:** Среднее  
**Митигация:**
- WAL режим
- Агрессивное кэширование
- План миграции на PostgreSQL

### Риск 2: Проблемы безопасности
**Вероятность:** Средняя  
**Влияние:** Критическое  
**Митигация:**
- Security тесты
- Code review
- Проверенные библиотеки

### Риск 3: Проблемы интеграции
**Вероятность:** Средняя  
**Влияние:** Высокое  
**Митигация:**
- Ранняя интеграция
- Переходный период
- Rollback план

---

## Roadmap

### MVP (6-8 недель)
- ✅ OAuth2 Password Grant
- ✅ Refresh Token Grant
- ✅ JWT токены (RS256)
- ✅ JWKS endpoint
- ✅ Rate limiting
- ✅ Аудит логирование
- ✅ Интеграция с Gateway и Agent Runtime

### Post-MVP

**Фаза 2: Authorization Code Flow (4-6 недель)**
- Authorization Code Grant + PKCE
- Consent screen UI
- Redirect URI validation

**Фаза 3: Client Credentials (2-3 недели)**
- Межсервисная аутентификация
- Service accounts

**Фаза 4: RBAC (4-6 недель)**
- Роли и разрешения
- Иерархия ролей
- Admin UI для управления

**Фаза 5: SSO (6-8 недель)**
- Интеграция с Google, GitHub
- SAML 2.0
- OpenID Connect

**Фаза 6: Advanced Security (4-6 недель)**
- Multi-factor authentication (MFA)
- Device fingerprinting
- Anomaly detection

**Фаза 7: PostgreSQL Migration (1-2 недели)**
- Миграция с SQLite на PostgreSQL
- Горизонтальное масштабирование
- Read replicas

---

## Оценка ресурсов

### Команда
- **Backend Developer:** 1 FTE
- **DevOps Engineer:** 0.5 FTE
- **QA Engineer:** 0.5 FTE
- **Итого:** 2 FTE

### Время
- **Минимум:** 25 дней (5 недель)
- **Максимум:** 38 дней (7.6 недель)
- **Реалистично:** 30-40 дней (6-8 недель)

### Стоимость (примерная)
- Backend Developer: 40 дней × $500/день = $20,000
- DevOps Engineer: 20 дней × $400/день = $8,000
- QA Engineer: 20 дней × $350/день = $7,000
- **Итого:** ~$35,000

---

## Критерии успеха

### Функциональные
- ✅ Пользователь может войти по login/password
- ✅ Пользователь может обновить access token
- ✅ Gateway валидирует JWT токены
- ✅ Refresh token ротируется корректно
- ✅ Reuse detection работает

### Нефункциональные
- ✅ Время ответа < 200ms (p95)
- ✅ Throughput > 100 RPS
- ✅ Coverage > 80%
- ✅ Доступность > 99.9%

### Безопасность
- ✅ Rate limiting работает
- ✅ Brute-force защита работает
- ✅ JWT токены валидируются корректно
- ✅ Security тесты проходят

---

## Следующие шаги

### Немедленные действия
1. ✅ Утвердить ТЗ и план
2. ⏳ Создать репозиторий/ветку
3. ⏳ Настроить окружение разработки
4. ⏳ Начать итерацию 0 (инфраструктура)

### Первая неделя
- Настроить Docker Compose
- Создать базовую структуру проекта
- Настроить SQLite и Redis
- Создать первые модели данных

### Первый месяц
- Реализовать OAuth2 Password Grant
- Реализовать Refresh Token Grant
- Интегрировать с Gateway
- Провести первые тесты

---

## SMTP Email Integration ✨ НОВОЕ

### Обзор

К базовому Auth Service добавлена полная SMTP интеграция для отправки email уведомлений при регистрации пользователей и других важных событиях.

### Функциональность

**Типы email:**
- Welcome email — при успешной регистрации
- Email confirmation — верификация email адреса
- Password reset — сброс пароля

### Архитектура

**Компоненты:**
- `EmailTemplateEngine` — рендеринг Jinja2 шаблонов
- `SMTPEmailSender` — асинхронная отправка через SMTP
- `EmailRetryService` — retry логика с exponential backoff
- `EmailNotificationService` — управление отправкой email
- `EmailService` — интеграция с основным сервисом

**Особенности:**
- Асинхронная обработка в background (не блокирует API)
- Retry логика с exponential backoff и jitter
- Graceful degradation (ошибки email не влияют на основной процесс)
- Поддержка различных SMTP провайдеров (Gmail, SendGrid, AWS SES и т.д.)
- MailHog для локальной разработки

### Конфигурация

```bash
# SMTP сервер
AUTH_SERVICE__SMTP_HOST=smtp.gmail.com
AUTH_SERVICE__SMTP_PORT=587
AUTH_SERVICE__SMTP_USERNAME=user@gmail.com
AUTH_SERVICE__SMTP_PASSWORD=app-password
AUTH_SERVICE__SMTP_FROM_EMAIL=noreply@codelab.com

# Опции
AUTH_SERVICE__SMTP_USE_TLS=true          # Использовать STARTTLS
AUTH_SERVICE__SMTP_TIMEOUT=30            # Timeout в секундах
AUTH_SERVICE__SMTP_MAX_RETRIES=3         # Максимум попыток

# Управление
AUTH_SERVICE__SEND_WELCOME_EMAIL=true
AUTH_SERVICE__REQUIRE_EMAIL_CONFIRMATION=true
AUTH_SERVICE__SEND_PASSWORD_RESET_EMAIL=true
```

### Новые Endpoints

**POST /api/v1/register** — обновлено
- При успешной регистрации отправляются email уведомления в background
- Ошибки email не влияют на результат (201 Created всё равно)

**GET /api/v1/confirm-email** — новый
- Подтверждение email адреса по токену
- Параметр: `token` (query)
- Ответ: 200 OK или 400 Bad Request

### API Endpoints для Email

Полная документация в разделе 11 файла [`TECHNICAL_SPECIFICATION.md`](TECHNICAL_SPECIFICATION.md#11-email-notifications-smtp-integration).

### Security

- ✅ Маскирование email адресов в логах
- ✅ SMTP credentials не логируются
- ✅ TLS/STARTTLS для безопасной передачи
- ✅ Tokens одноразовые (удаляются после использования)
- ✅ Exponential backoff предотвращает spam

### Тестирование

**84 тестов**: 70 unit + 14 integration
- Покрытие: 85%
- Phases 9-10 успешно завершены
- Все тесты проходят

### Документация

1. [Email Setup Guide](EMAIL_SETUP.md) — настройка SMTP для различных провайдеров
2. [Integration Tests Guide](INTEGRATION_TESTS.md) — запуск integration тестов
3. [QA Report](QA_REPORT_SMTP.md) — результаты QA тестирования

---

## Заключение

Создана полная документация для реализации Auth Service:

1. **Техническое задание** — детальные требования и спецификации
2. **План реализации** — пошаговый план на 12 итераций
3. **Интеграционные точки** — детальная интеграция с существующими сервисами
4. **README** — руководство пользователя и разработчика

Проект готов к началу реализации. Все архитектурные решения приняты с учетом:
- Существующей архитектуры CodeLab
- Требований безопасности
- Производительности и масштабируемости
- Простоты развертывания (SQLite для MVP)
- Возможности миграции на PostgreSQL

**Статус:** ✅ Готово к реализации  
**Следующий шаг:** Начать итерацию 0 (Подготовка инфраструктуры)

---

## Контакты

**Разработчик:** Sergey Penkovsky  
**Email:** sergey.penkovsky@gmail.com  
**Проект:** CodeLab Auth Service  
**Дата:** 2026-01-05
