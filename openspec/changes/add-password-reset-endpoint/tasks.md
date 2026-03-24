# Задачи реализации: Endpoint сброса пароля

**Версия:** 1.0.0  
**Дата:** 2026-03-24  
**Статус:** Implementation Checklist

---

## 1. Database & Models

- [x] 1.1 Создать Alembic миграцию для таблицы `password_reset_tokens`
  - Таблица с колонками: id (UUID), user_id (FK), token_hash (VARCHAR unique), created_at, expires_at, used_at
  - Индексы на: user_id, expires_at, token_hash
  - Проверить миграция обратима (можно откатить)

- [x] 1.2 Создать SQLAlchemy модель `PasswordResetToken` в `app/models/password_reset_token.py`
  - Отношение к User модели через foreign key
  - Проверка is_expired() методом
  - Проверка is_used() методом

- [x] 1.3 Обновить `app/models/__init__.py` для экспорта новой модели

---

## 2. Core Services

- [x] 2.1 Создать `app/services/password_reset_service.py` с основной логикой
  - Функция `create_token(user_id: UUID) -> str` - генерирует и сохраняет токен
  - Функция `verify_token(token: str) -> UUID | None` - верифицирует токен, возвращает user_id если валиден
  - Функция `mark_token_used(token: str) -> bool` - отмечает токен как использованный
  - Функция `cleanup_expired_tokens()` - удаляет истёкшие токены из БД

- [x] 2.2 Реализовать криптографическую генерацию токенов
  - Использовать `secrets.token_urlsafe(32)` для генерации
  - SHA-256 хеширование перед сохранением в БД
  - Constant-time сравнение при верификации

- [x] 2.3 Реализовать логику проверки сроков действия
  - Токен действует ровно 30 минут
  - При верификации проверять: exists + not expired + not used

- [x] 2.4 Интеграция с сервисом пользователей
  - Использовать `UserService.get_by_email()` для поиска пользователя
  - Проверка что пользователь exists перед созданием токена
  - Не раскрывать информацию о существовании пользователя в responses

---

## 3. Email Notifications

- [x] 3.1 Обновить `app/services/email_notifications.py`
  - Добавить функцию `send_password_reset_email(email: str, reset_url: str, expiry_hours: float)`
  - Использовать существующую систему шаблонов для password_reset

- [x] 3.2 Создать или обновить email шаблоны в `app/templates/emails/password_reset/`
  - `subject.txt` - тема письма
  - `template.html` - HTML версия письма
  - Переменные для подстановки: user_name, reset_url, token_expiry_hours, support_email

- [x] 3.3 Реализовать асинхронную отправку письма
  - Отправка в background task (asyncio.create_task или BackgroundTasks)
  - Не блокировать endpoint response
  - Retry логика для временных ошибок SMTP (3 попытки с backoff)

- [x] 3.4 Логирование email отправки
  - Логировать успешную отправку (email masked)
  - Логировать ошибки без раскрытия credentials или токена
  - Уровень INFO для успеха, WARNING для ошибок

---

## 4. API Endpoints

- [x] 4.1 Создать `app/api/v1/password_reset.py` модуль для endpoints

- [x] 4.2 Реализовать endpoint `POST /api/v1/auth/password-reset/request`
  - Параметр: email (string, required)
  - Валидация: проверить формат email
  - Логика: найти пользователя, создать токен, отправить email
  - Response: всегда 200 OK с сообщением "Инструкции отправлены" (безопасность)
  - Rate limiting: максимум 3 запроса за 1 час на пользователя/email

- [x] 4.3 Реализовать endpoint `POST /api/v1/auth/password-reset/confirm`
  - Параметры: token (string), password (string), password_confirm (string)
  - Валидация: 
    - Проверить что token валиден (exists, not expired, not used)
    - Проверить что password соответствует требованиям (8-64 символов, uppercase, lowercase, digit, special char)
    - Проверить что password и password_confirm совпадают
  - Логика: верифицировать токен, изменить пароль пользователя, отметить токен как использованный
  - Response: 200 OK с сообщением "Пароль изменён успешно"
  - Errors: 400 для невалидного токена/пароля

- [x] 4.4 Регистрация нового роутера в `app/main.py`
  - Добавить импорт `from app.api.v1 import password_reset`
  - Зарегистрировать router: `app.include_router(password_reset.router)`

---

## 5. Security & Rate Limiting

- [x] 5.1 Реализовать rate limiting для password-reset/request
  - Ограничение по user email: 3 запроса за 1 час
  - Ограничение по IP адресу: 5 запросов за 1 час (слабее, для защиты от distributed)
  - Использовать in-memory counter с TTL или существующий rate limiter сервис

- [x] 5.2 Реализовать брут-форс защиту для password-reset/confirm
  - Ограничение по IP адресу: максимум 10 неудачных попыток за 5 минут
  - Блокировка IP на 15 минут после превышения
  - Логирование всех неудачных попыток как WARNING

- [x] 5.3 Реализовать логирование security событий
  - Логировать создание токена (email masked)
  - Логировать успешное подтверждение (password change)
  - Логировать все failed attempts (invalid token, expired token, brute-force detection)
  - Использовать `AuditService` для audit trail

- [x] 5.4 Обновить конфигурацию `app/core/config.py` если нужно
  - Убедиться что SMTP параметры configured
  - Добавить параметры rate limiting (если needed): PASSWORD_RESET_REQUEST_LIMIT (3/hour), PASSWORD_RESET_CONFIRM_LIMIT (10/5min)

---

## 6. Integration & Testing

- [x] 6.1 Написать unit тесты в `tests/` (или `test_` prefix)
  - test_token_generation_format - проверить формат и entropy
  - test_token_hashing_deterministic - проверить детерминизм хеша
  - test_token_expiration - проверить что истёкший токен отвергается
  - test_single_use_enforcement - проверить что повторное использование невозможно
  - test_password_validation_weak - слабый пароль должен быть отвергнут
  - test_password_validation_strong - сильный пароль должен приниматься
  - test_email_not_sent_for_nonexistent_user - письмо не отправлено но 200 OK

- [x] 6.2 Написать integration тесты
  - test_password_reset_request_success - полный flow запроса
  - test_password_reset_confirm_success - полный flow подтверждения
  - test_password_reset_confirm_with_expired_token - истёкший токен
  - test_password_reset_confirm_with_used_token - уже использованный токен
  - test_rate_limiting_request - превышение лимита на requests
  - test_rate_limiting_confirm - превышение лимита на попытки
  - test_brute_force_detection - обнаружение pattern брут-форса

- [x] 6.3 Написать E2E тест полного цикла
  - Запросить сброс пароля → Получить письмо → Извлечь ссылку → Перейти по ссылке → Ввести новый пароль → Вход с новым паролем

- [x] 6.4 Миграция данных и проверка совместимости
  - Запустить миграцию на staging
  - Убедиться что существующие users не затронуты
  - Проверить что endpoints не ломают existing API контрактов

- [x] 6.5 Проверка логирования и мониторинга
  - Проверить что sensitive данные (токены, пароли) не логируются
  - Проверить что email address masked в логах
  - Настроить alerts для security events (brute-force detection)

---

## 7. Documentation & Cleanup

- [x] 7.1 Обновить README.md или API документацию
  - Добавить информацию о новых endpoints
  - Добавить примеры requests/responses
  - Добавить информацию о rate limits

- [x] 7.2 Обновить IMPLEMENTATION_PLAN.md или PROJECT_SUMMARY.md
  - Отметить что password reset реализовано
  - Обновить list of endpoints

- [x] 7.3 Проверить что все файлы следуют стилю проекта
  - Использовать существующие паттерны из других services
  - Следовать прямим из pyproject.toml (черный форматер, flake8, типирование)
  - Добавить type hints для всех функций

- [x] 7.4 Cleanup и final review
  - Проверить что все imports работают
  - Убедиться что нет unused imports или code
  - Проверить что миграция не ломает существующие constraints

---

## Estimation & Ordering

**Рекомендуемый порядок выполнения:**

1. **First**: Группы 1-2 (Database & Models, Core Services) - это foundation
2. **Second**: Группа 3 (Email Notifications) - email infrastructure уже есть, интеграция простая
3. **Third**: Группа 4 (API Endpoints) - endpoints dependят на services
4. **Fourth**: Группа 5 (Security & Rate Limiting) - security features добавляются в endpoints
5. **Fifth**: Группа 6 (Integration & Testing) - тесты после реализации
6. **Finally**: Группа 7 (Documentation & Cleanup) - документация в конце

**Примерная стоимость времени:**
- Database & Models: 1-2 часа (создание миграции, модели)
- Core Services: 2-3 часа (логика, криптография, cleanup)
- Email: 1 час (интеграция с существующей системой)
- API Endpoints: 2-3 часа (endpoints, валидация, response formats)
- Security: 1-2 часа (rate limiting, логирование, audit)
- Testing: 3-4 часа (unit, integration, E2E тесты)
- Documentation: 1 час (README, comments)

**Итого: ~11-15 часов разработки**

---

## Verification Checklist

После завершения всех задач, убедиться:

- [x] Все endpoints работают и возвращают правильные response codes
- [x] Rate limiting работает и блокирует после лимита
- [x] Email отправляется асинхронно и не блокирует endpoints
- [x] Токены генерируются криптографически стойким способом
- [ ] Все тесты проходят (unit + integration + E2E)
- [x] Нет sensitive данных в логах
- [ ] Миграция успешна на staging/production
- [ ] API документация обновлена
- [x] Performance приемлемо (no N+1 queries, indexing правильное)
