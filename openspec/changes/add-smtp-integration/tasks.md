# Tasks: SMTP Email Integration для CodeLab Auth Service

**Версия:** 1.0.0  
**Дата:** 2026-03-23  
**Статус:** Implementation Phase

---

## 📋 Задачи реализации

### Phase 1: Подготовка проекта и конфигурация

- [x] Добавить зависимости в `pyproject.toml`: `aiosmtplib` и `jinja2`
- [x] Убедиться что зависимости установлены: `uv sync`
- [x] Расширить `app/core/config.py` с SMTP параметрами:
   - [x] `smtp_host` (строка, обязательный)
   - [x] `smtp_port` (целое число, обязательный)
   - [x] `smtp_username` (строка, опциональный)
   - [x] `smtp_password` (строка, опциональный, чувствительный)
   - [x] `smtp_from_email` (строка, обязательный, по умолчанию "noreply@codelab.com")
   - [x] `smtp_use_tls` (булево, по умолчанию `True`)
   - [x] `smtp_timeout` (целое число, по умолчанию 30 сек)
   - [x] `smtp_max_retries` (целое число, по умолчанию 3)
   - [x] `send_welcome_email` (булево, по умолчанию `True`)
   - [x] `require_email_confirmation` (булево, по умолчанию `True`)
   - [x] `send_password_reset_email` (булево, по умолчанию `True`)
- [x] Обновить `.env.example` с SMTP примерами
- [x] Создать миграцию БД для таблицы `email_confirmation_tokens`:
   - [x] `id` (UUID primary key)
   - [x] `user_id` (Foreign key на users)
   - [x] `token` (String, unique index)
   - [x] `expires_at` (DateTime UTC)
   - [x] `created_at` (DateTime UTC, auto-generated)
- [x] Запустить миграцию БД

### Phase 2: Реализация Email Template Engine

- [x] Создать класс `EmailMessage` в `app/services/email_templates.py`:
   - [x] Поле `subject: str` (тема письма)
   - [x] Поле `html_body: str` (HTML версия)
   - [x] Поле `text_body: str` (текстовая версия)
   - [x] Поле `to: str` (адрес получателя)
   - [x] Поле `from_: str` (адрес отправителя, по умолчанию из конфига)
   - [x] Поле `template_name: str` (имя использованного шаблона для логирования)
   - [x] Метод `as_string() -> str` (для передачи в SMTP)
- [x] Создать класс `EmailTemplateEngine` в `app/services/email_templates.py`:
   - [x] Инициализация с `template_dir` и Jinja2 с `autoescape=True`
   - [x] Асинхронный метод `render_template(template_name: str, context: dict) -> EmailMessage`
   - [x] Метод обработки шаблонов (загрузка, рендеринг HTML и текста)
   - [x] Обработка исключений при загрузке несуществующих шаблонов
- [x] Создать структуру директорий `app/templates/emails/`:
   - [x] `app/templates/emails/base.html` (базовый layout для всех писем)
   - [x] `app/templates/emails/welcome/` (приветственное письмо)
   - [x] `app/templates/emails/confirmation/` (подтверждение email)
   - [x] `app/templates/emails/password_reset/` (сброс пароля)
- [x] Создать HTML шаблон welcome письма с переменными: `username`, `email`, `activation_link`, `registration_date`
- [x] Создать HTML шаблон confirmation письма с переменными: `username`, `confirmation_link`, `expires_at`
- [x] Создать HTML шаблон password_reset письма с переменными: `username`, `reset_link`, `expires_at`
- [x] Для каждого шаблона создать файлы: `template.html`, `subject.txt`
- [x] Добавить стили CSS в base.html для корректного отображения в email клиентах
- [x] Добавить функцию экспорта EmailTemplateEngine в `app/services/__init__.py`

### Phase 3: Реализация SMTP Email Sender

- [x] Создать класс `SMTPEmailSender` в `app/services/email_sender.py`:
   - [x] Асинхронный метод `send_email(message: EmailMessage, timeout: int) -> bool`
   - [x] Метод создания SMTP соединения `_create_smtp_connection() -> SMTP`
   - [x] Поддержка TLS/STARTTLS при `smtp_use_tls=True`
   - [x] Поддержка базовой аутентификации (username/password)
   - [x] Обработка ошибок:
     - [x] `SMTPAuthenticationError` → логировать CRITICAL, вернуть False
     - [x] `SMTPServerError` (5xx) → логировать ERROR, вернуть False
     - [x] `SMTPServerError` (4xx) → пробросить исключение для retry
     - [x] `asyncio.TimeoutError` → пробросить для retry
     - [x] `ConnectionError` → пробросить для retry
   - [x] Логирование успешной отправки (без логирования credentials)
   - [x] Маскирование email адресов в логах
- [x] Добавить функцию экспорта SMTPEmailSender в `app/services/__init__.py`

### Phase 4: Реализация Email Retry Service

- [x] Создать класс `EmailRetryService` в `app/services/email_retry.py`:
   - [x] Асинхронный метод `send_with_retry(message: EmailMessage, max_retries: int, base_delay: int) -> bool`
   - [x] Метод вычисления exponential backoff: `_calculate_backoff(attempt: int, base_delay: int, max_backoff: int) -> float`
   - [x] Формула: `backoff = base_delay * (2 ^ attempt)`, capped at max_backoff
   - [x] Добавить jitter (±10%) к backoff для избежания thundering herd
   - [x] Метод определения повторяемых ошибок: `_should_retry(error: Exception) -> bool`
   - [x] Метод логирования попыток: `_log_attempt(message: EmailMessage, attempt: int, error: Optional[Exception])`
   - [x] Обработка max_retries (по умолчанию 3)
   - [x] Логирование каждой попытки для аудита
- [x] Добавить функцию экспорта EmailRetryService в `app/services/__init__.py`

### Phase 5: Реализация Email Notification Service

- [x] Создать класс `EmailNotificationService` в `app/services/email_notifications.py`:
   - [x] Инъекция зависимостей: `EmailTemplateEngine`, `SMTPEmailSender`, `EmailRetryService`
   - [x] Асинхронный метод `send_welcome_email(user: User, background: bool = True) -> bool`
   - [x] Асинхронный метод `send_confirmation_email(user: User, token: str, background: bool = True) -> bool`
   - [x] Асинхронный метод `send_password_reset_email(user: User, reset_token: str) -> bool`
   - [x] Внутренний метод `_send_async(message: EmailMessage, retry: bool = True) -> bool`
   - [x] Проверка настроек перед отправкой (`send_welcome_email`, `require_email_confirmation` и т.д.)
   - [x] Создание контекста для шаблонов (username, email, ссылки, даты)
   - [x] Обработка ошибок с graceful degradation (не прерывать основной процесс)
   - [x] Логирование всех попыток отправки (успех и ошибки)
- [x] Добавить функцию экспорта EmailNotificationService в `app/services/__init__.py`
- [x] Добавить singleton инициализацию сервисов в `app/main.py` (или dependency injection)

### Phase 6: Расширение существующих сервисов

- [x] Обновить `app/services/email_service.py`:
   - [x] Реализовать метод `send_confirmation_email(user: User) -> bool` (использовать EmailNotificationService)
   - [x] Добавить метод `generate_confirmation_token(user_id: UUID) -> str`
   - [x] Добавить метод `verify_confirmation_token(token: str) -> Optional[User]`
   - [x] Логирование операций с токенами
- [x] Добавить Pydantic модель `EmailConfirmationToken` в `app/models/`:
   - [x] Поля: `id`, `user_id`, `token`, `expires_at`, `created_at`
   - [x] Создать ORM модель если нужна
- [x] Убедиться что зависимости могут быть получены через dependency injection в API

### Phase 7: Интеграция в API (регистрация)

- [x] Обновить endpoint `POST /api/v1/register` в `app/api/v1/register.py`:
   - [x] После успешной регистрации пользователя:
     - [x] Создать задачу для отправки welcome email через `asyncio.create_task()`
     - [x] Если `require_email_confirmation=True`, создать задачу для confirmation email
   - [x] Убедиться что ошибки email отправки не прерывают регистрацию
   - [x] Обработка исключений при создании background task с логированием
   - [x] API ответ остается 201 Created с UserRegistrationResponse независимо от статуса email
- [x] Создать endpoint `GET /api/v1/confirm-email` для подтверждения email:
   - [x] Параметр: `token` (query параметр)
   - [x] Вызов `email_service.verify_confirmation_token(token)`
   - [x] Ответ 200 OK если успешно, 400 Bad Request если токен истек/невалиден
   - [x] Логирование всех попыток подтверждения

### Phase 8: Интеграция в Audit logging

- [x] Добавить логирование в `app/services/audit_service.py`:
   - [x] `log_email_sent(user_id: UUID, template_name: str, recipient: str)`
   - [x] `log_email_failed(user_id: UUID, template_name: str, error: str, retry_count: int)`
   - [x] `log_email_confirmation_token_generated(user_id: UUID, token_hash: str)`
   - [x] `log_email_confirmation_success(user_id: UUID)`
   - [x] `log_email_confirmation_failed(token: str, reason: str)`
- [x] Вызовы audit методов в email сервисах при отправке и ошибках

### Phase 9: Написание Unit тестов

- [ ] Создать `tests/test_email_templates.py`:
   - [ ] Тест загрузки и рендеринга простого шаблона
   - [ ] Тест рендеринга с динамическими переменными
   - [ ] Тест обработки несуществующего шаблона
   - [ ] Тест XSS защиты (спецсимволы escapeятся)
   - [ ] Тест создания текстовой версии из HTML
- [ ] Создать `tests/test_email_sender.py`:
   - [ ] Mock SMTP сервера для тестирования
   - [ ] Тест успешной отправки с TLS
   - [ ] Тест отправки без TLS
   - [ ] Тест обработки SMTPAuthenticationError (не retry)
   - [ ] Тест обработки SMTPServerError 5xx (не retry)
   - [ ] Тест обработки SMTPServerError 4xx (retry)
   - [ ] Тест обработки timeout (retry)
   - [ ] Тест обработки ConnectionError (retry)
- [ ] Создать `tests/test_email_retry.py`:
   - [ ] Тест вычисления exponential backoff
   - [ ] Тест jitter добавления к backoff
   - [ ] Тест retry до max_retries
   - [ ] Тест остановки после успешной отправки
   - [ ] Тест определения retryable vs permanent ошибок
- [ ] Создать `tests/test_email_notifications.py`:
   - [ ] Тест send_welcome_email с правильным контекстом
   - [ ] Тест send_confirmation_email с токеном
   - [ ] Тест send_password_reset_email
   - [ ] Тест graceful degradation при ошибке email
   - [ ] Тест что конфигурационные флаги (send_welcome_email и т.д.) работают
- [ ] Создать `tests/test_email_service.py`:
   - [ ] Тест generate_confirmation_token
   - [ ] Тест verify_confirmation_token с валидным токеном
   - [ ] Тест verify_confirmation_token с истекшим токеном
   - [ ] Тест verify_confirmation_token с невалидным токеном
   - [ ] Тест одноразового использования токена
- [ ] Создать `tests/test_registration_with_email.py` (интеграционный тест):
   - [ ] Тест регистрации пользователя с отправкой welcome email
   - [ ] Тест регистрации с отправкой confirmation email
   - [ ] Тест что регистрация успешна даже если email отправка неудачна
   - [ ] Тест endpoint подтверждения email

### Phase 10: Написание Integration тестов

- [ ] Создать `tests/integration/test_smtp_integration.py`:
   - [ ] Тест полного цикла: регистрация → отправка welcome → confirmation email
   - [ ] Тест retry логики при временных ошибках SMTP
   - [ ] Тест graceful degradation при недоступном SMTP сервере
- [ ] Проверить тесты с real SMTP сервером (MailHog в dev) или mock
- [ ] Убедиться что все тесты проходят: `pytest`

### Phase 11: Документация и примеры

- [ ] Обновить `docs/IMPLEMENTATION_PLAN.md` с разделом о SMTP интеграции:
   - [ ] Описание архитектуры компонентов
   - [ ] Диаграмма data flow
   - [ ] Инструкции по конфигурации SMTP
- [ ] Обновить `docs/TECHNICAL_SPECIFICATION.md`:
   - [ ] Описание новых endpoints (`POST /api/v1/register`, `GET /api/v1/confirm-email`)
   - [ ] Параметры конфигурации
   - [ ] Обработка ошибок
   - [ ] Примеры API запросов/ответов
- [ ] Создать `docs/EMAIL_SETUP.md`:
   - [ ] Инструкции по настройке SMTP для different providers (SendGrid, AWS SES, MailHog)
   - [ ] Примеры `.env` конфигурации
   - [ ] Troubleshooting guide
- [ ] Обновить `README.md` с краткой информацией о email функции
- [ ] Добавить примеры использования в docstrings всех публичных методов

### Phase 12: Финализация и проверка качества

- [ ] Проверка покрытия тестами (целевой уровень >= 80%)
- [ ] Запуск всех тестов: `pytest --cov`
- [ ] Проверка linting: `ruff check .`
- [ ] Проверка type hints: `mypy app/`
- [ ] Убедиться что нет логирования SMTP credentials в production логах
- [ ] Убедиться что email адреса маскируются в логах
- [ ] Code review чек-лист:
   - [ ] Все методы имеют type hints
   - [ ] Все методы имеют docstrings
   - [ ] Нет hard-coded значений (все в config)
   - [ ] Error handling следует спецификациям
   - [ ] Async/await правильно используется
   - [ ] Нет утечек SMTP credentials
- [ ] Проверка производительности:
   - [ ] Асинхронная отправка не блокирует API
   - [ ] Retry логика не создает бесконечные циклы
   - [ ] Memory usage приемлем при большом количестве email

### Phase 13: Развертывание и мониторинг

- [ ] Подготовка миграции БД для production
- [ ] Обновление документации по deployment
- [ ] Настройка мониторинга успешности отправки email
- [ ] Создание dashboards для отслеживания:
   - [ ] Количество отправленных email
   - [ ] Процент успешных отправок
   - [ ] Среднее время доставки
   - [ ] Ошибки по типам
- [ ] Настройка алертов на критические ошибки (SMTPAuthenticationError, persistent failures)

---

## 📊 Зависимости между фазами

```
Phase 1 (Конфигурация)
    ↓
Phase 2 (Templates) ← Phase 3 (Sender) ← Phase 4 (Retry)
    ↓                    ↓                    ↓
    └────────────────────┴────────────────────┘
                        ↓
Phase 5 (Notifications Service)
    ↓
Phase 6 (Расширение сервисов)
    ↓
Phase 7 (API интеграция) + Phase 8 (Audit) + Phase 9 (Unit тесты)
    ↓
Phase 10 (Integration тесты)
    ↓
Phase 11 (Документация)
    ↓
Phase 12 (QA и чек-листы)
    ↓
Phase 13 (Развертывание)
```

---

## ✅ Критерии готовности

Артефакт считается готовым к реализации когда:
- ✅ Все задачи разбиты на конкретные, выполнимые действия
- ✅ Задачи упорядочены с учетом зависимостей
- ✅ Каждая задача может быть выполнена независимо в правильном порядке
- ✅ Включены задачи для кода, тестов, конфигурации, документации
- ✅ Критерии готовности каждой фазы ясны
