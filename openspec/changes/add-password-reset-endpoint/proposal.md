## Why

Пользователи часто забывают пароли к учётным записям, что приводит к потере доступа к сервису. Требуется реализовать безопасный механизм восстановления пароля, позволяющий пользователям восстановить доступ к своим аккаунтам через верификацию по email, без необходимости вмешательства администратора.

## What Changes

- **Модель базы данных для токенов сброса:** Создание таблицы `password_reset_tokens` для хранения одноразовых токенов со сроком действия
- **REST API endpoints:** Добавление endpoint для запроса сброса пароля (`POST /api/v1/auth/password-reset/request`) и endpoint для подтверждения сброса (`POST /api/v1/auth/password-reset/confirm`)
- **Email уведомления:** Отправка письма с ссылкой для сброса пароля при запросе восстановления доступа
- **Валидация и безопасность:** Реализация механизма генерации безопасных токенов, проверки срока действия, однократного использования и rate-limiting для защиты от brute-force атак
- **Интеграция с существующей инфраструктурой:** Использование SMTP интеграции и email-template системы из предыдущего изменения `add-smtp-integration`

## Capabilities

### New Capabilities

- `password-reset-token`: Модель, валидация и логика управления токенами сброса пароля, включая генерацию, сохранение и проверку срока действия
- `password-reset-api`: REST API endpoints для запроса сброса пароля и подтверждения с установкой нового пароля
- `password-reset-notifications`: Email уведомления пользователю при запросе сброса пароля с безопасной ссылкой для восстановления доступа

### Modified Capabilities

- `user-authentication`: Расширение функционала аутентификации добавлением процесса восстановления пароля
- `email-notifications`: Добавление нового типа уведомления (password_reset) к существующей системе email-уведомлений

## Impact

**Новые файлы:**
- `app/models/password_reset_token.py` - модель для хранения токенов сброса пароля
- `app/api/v1/password_reset.py` - endpoints для сброса пароля
- `app/services/password_reset_service.py` - бизнес-логика сброса пароля
- `app/templates/emails/password_reset/` - шаблоны писем (существуют в текущей реализации)

**Изменяемые файлы:**
- `app/models/user.py` - возможно добавление вспомогательных полей для tracking запросов на сброс
- `app/main.py` - регистрация нового blueprint/router для password_reset endpoints
- `app/services/email_notifications.py` - добавление нового типа уведомления (password_reset)
- `migration/versions/` - новая миграция Alembic для создания таблицы `password_reset_tokens`

**Новые зависимости:** Нет новых зависимостей, используются существующие библиотеки (SQLAlchemy, FastAPI, aiosmtplib)

**Новые таблицы БД:**
- `password_reset_tokens` с колонками: id, user_id, token, token_hash, created_at, expires_at, used_at

**API изменения:**
- Новые endpoints: `POST /api/v1/auth/password-reset/request` и `POST /api/v1/auth/password-reset/confirm`
- No breaking changes в существующих endpoints

**Безопасность:**
- Использование одноразовых токенов со сроком действия (30 минут)
- Rate-limiting на requests сброса пароля (максимум 3 запроса за 1 час на пользователя)
- Хеширование токенов в БД для защиты от утечек
- Отправка письма только если пользователь с таким email существует (но не раскрыть информацию о существовании аккаунта в response)
