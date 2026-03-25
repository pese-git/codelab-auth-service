## 1. Конфигурация и подготовка

- [x] 1.1 Добавить переменные окружения в `app/core/config.py` для rate limiting (REGISTRATION_RATE_LIMIT, default=10)
- [x] 1.2 Добавить переменную окружения REQUIRE_EMAIL_CONFIRMATION (default=true) в config.py
- [x] 1.3 Добавить переменную окружения SUGGEST_USERNAMES (default=true) в config.py
- [x] 1.4 Добавить переменную окружения AUDIT_LOG_RETENTION_DAYS (default=90) в config.py
- [x] 1.5 Убедиться что SMTP конфигурация существует в config.py для отправки email (требуется для email confirmation)

## 2. Pydantic Schemas для регистрации

- [x] 2.1 Создать schema `UserRegister` в `app/schemas/user.py` с полями: email, username, password
- [x] 2.2 Добавить валидацию email в `UserRegister` - использовать EmailStr или regex для RFC 5322
- [x] 2.3 Добавить валидацию username в `UserRegister` - 3-20 символов, буквы/цифры/-/_
- [x] 2.4 Добавить валидацию пароля в `UserRegister` - минимум 8 символов, максимум 128
- [x] 2.5 Создать response schema `UserRegistrationResponse` с полями: id, email, username, created_at
- [x] 2.6 Убедиться что response schema НЕ включает password_hash или другие чувствительные данные

## 3. Database и User Model

- [x] 3.1 Проверить что User модель имеет unique constraint на email в базе данных
- [x] 3.2 Проверить что User модель имеет unique constraint на username в базе данных
- [x] 3.3 Добавить field `email_confirmed` (boolean, default=False) в User модель для email confirmation
- [x] 3.4 Создать миграцию Alembic для добавления `email_confirmed` поля если требуется
- [x] 3.5 Убедиться что password_hash field существует и использует bcrypt хеширование

## 4. User Service методы

- [x] 4.1 Добавить метод `get_user_by_email()` в `UserService` для проверки существования email
- [x] 4.2 Добавить метод `get_user_by_username()` в `UserService` для проверки существования username
- [x] 4.3 Добавить метод `create_user()` в `UserService` с параметрами email, username, password
- [x] 4.4 Реализовать хеширование пароля в `create_user()` используя bcrypt с cost factor 12
- [x] 4.5 Добавить проверку уникальности email перед созданием пользователя в `create_user()`
- [x] 4.6 Добавить проверку уникальности username перед созданием пользователя в `create_user()`
- [x] 4.7 Обработать database constraint violations (IntegrityError) при race conditions в `create_user()`
- [x] 4.8 Добавить метод для генерации suggestions username если SUGGEST_USERNAMES включен
- [x] 4.9 Убедиться что методы используют параметризованные запросы (SQLAlchemy ORM защищает от SQL injection)

## 5. API Endpoint реализация

- [x] 5.1 Создать новый файл `app/api/v1/register.py` с FastAPI router
- [x] 5.2 Создать POST endpoint `/register` в router (будет доступен как /api/v1/register)
- [x] 5.3 Добавить параметр request body с типом `UserRegister` schema
- [x] 5.4 Реализовать основную логику обработки регистрации в endpoint
- [x] 5.5 Возвращать 201 Created статус при успешной регистрации с Location header
- [x] 5.6 Возвращать response с типом `UserRegistrationResponse` при успехе
- [x] 5.7 Обработать 409 Conflict ошибку для дублирования email с сообщением "Email already registered"
- [x] 5.8 Обработать 409 Conflict ошибку для дублирования username с сообщением "Username already taken"
- [x] 5.9 Если SUGGEST_USERNAMES включен, включить список suggestion username в 409 response для username конфликта
- [x] 5.10 Обработать 422 Unprocessable Entity ошибку для validation failures (FastAPI делает это автоматически)
- [x] 5.11 Обработать 429 Too Many Requests ошибку для rate limiting (middleware обработает)

## 6. Rate Limiting интеграция

- [x] 6.1 Проверить что RateLimiter middleware применяется ко всем endpoint'ам в приложении
- [x] 6.2 Создать или обновить rate limit конфигурацию для `/api/v1/register` endpoint
- [x] 6.3 Установить rate limit на 10 requests/minute по IP адресу для регистрации
- [x] 6.4 Убедиться что rate limiter возвращает Retry-After header в 429 response
- [x] 6.5 Настроить rate limiter на использование REGISTRATION_RATE_LIMIT из config вместо hardcoded значения

## 7. Audit Logging

- [x] 7.1 Реализовать логирование события REGISTRATION_ATTEMPT_SUCCESS с email, username, user_id, timestamp
- [x] 7.2 Реализовать логирование события REGISTRATION_ATTEMPT_FAILED с email, username, failure_reason, client_ip, timestamp
- [x] 7.3 Реализовать логирование события REGISTRATION_DUPLICATE_EMAIL с attempted_email, existing_user_id
- [x] 7.4 Реализовать логирование события REGISTRATION_DUPLICATE_USERNAME с attempted_username, existing_user_id
- [x] 7.5 Добавить логирование client_ip и user_agent в audit logs где применимо
- [x] 7.6 Убедиться что пароли НЕ логируются в audit logs
- [x] 7.7 Интегрировать AuditService в register endpoint для логирования всех событий
- [x] 7.8 Установить AUDIT_LOG_RETENTION_DAYS в config для управления периодом хранения логов

## 8. Email Confirmation (опциональное)

- [x] 8.1 Создать метод `send_confirmation_email()` для отправки email с confirmation ссылкой
- [x] 8.2 Создать метод `generate_confirmation_token()` для генерации безопасного token'а
- [x] 8.3 Добавить логику в `create_user()` для установки email_confirmed=False если REQUIRE_EMAIL_CONFIRMATION=true
- [x] 8.4 Создать endpoint `/confirm-email` для верификации confirmation token'а
- [x] 8.5 Реализовать обновление `email_confirmed` флага после успешного подтверждения email
- [x] 8.6 Добавить логирование событий EMAIL_CONFIRMATION_SENT и EMAIL_CONFIRMED в audit logs
- [x] 8.7 Обработать expired confirmation token'ы с корректным error message
- [x] 8.8 Если REQUIRE_EMAIL_CONFIRMATION=false, пропустить email confirmation логику (установить email_confirmed=true)

## 9. Timing Attack защита

- [x] 9.1 Убедиться что при проверке дублирования email, система всегда выполняет полное хеширование пароля
- [x] 9.2 Убедиться что при проверке дублирования username, система всегда выполняет полное хеширование пароля
- [x] 9.3 Убедиться что время ответа примерно одинаково для существующего и нового email/username
- [x] 9.4 Добавить примерно одинаковое количество обработки для успеха и failure сценариев

## 10. Response Headers и API integration

- [x] 10.1 Убедиться что response содержит Content-Type: application/json для всех responses
- [x] 10.2 Убедиться что response содержит Cache-Control: no-store для защиты sensitive данных
- [x] 10.3 Убедиться что security headers присутствуют (X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security)
- [x] 10.4 Добавить Location header с URL нового ресурса в 201 response

## 11. FastAPI приложение интеграция

- [x] 11.1 Импортировать router из `app/api/v1/register.py` в `app/api/v1/__init__.py`
- [x] 11.2 Зарегистрировать router в `app/main.py` с prefix `/api/v1`
- [x] 11.3 Убедиться что endpoint видимый в OpenAPI documentation (`/docs`)
- [x] 11.4 Убедиться что endpoint видимый в ReDoc documentation (`/redoc`)
- [x] 11.5 Убедиться что CORS включен для публичного endpoint регистрации в `app/main.py`

## 12. Unit тесты

- [-] 12.1 Создать test файл `tests/test_register.py`
- [-] 12.2 Написать тест для успешной регистрации с валидными данными
- [-] 12.3 Написать тест для дублирования email (409 Conflict)
- [-] 12.4 Написать тест для дублирования username (409 Conflict)
- [-] 12.5 Написать тест для невалидного email формата (422 Unprocessable Entity)
- [-] 12.6 Написать тест для невалидного username (слишком короткий, слишком длинный, спецсимволы)
- [-] 12.7 Написать тест для невалидного пароля (< 8 символов, > 128 символов)
- [-] 12.8 Написать тест для отсутствующих обязательных полей (400/422)
- [-] 12.9 Написать тест для extra fields в request (должны игнорироваться)
- [-] 12.10 Написать тест для empty string values валидации

## 13. Integration тесты

- [-] 13.1 Написать integration тест для успешного flow регистрации end-to-end
- [-] 13.2 Написать тест для timing attack защиты (одинаковое время для существующего/нового email)
- [-] 13.3 Написать тест для rate limiting (11-я request должна получить 429)
- [-] 13.4 Написать тест для Retry-After header в 429 response
- [-] 13.5 Написать тест для audit logging REGISTRATION_ATTEMPT_SUCCESS события
- [-] 13.6 Написать тест для audit logging REGISTRATION_ATTEMPT_FAILED события
- [-] 13.7 Написать тест для audit logging REGISTRATION_DUPLICATE_EMAIL события
- [-] 13.8 Написать тест для audit logging REGISTRATION_DUPLICATE_USERNAME события
- [-] 13.9 Написать тест для email confirmation flow если REQUIRE_EMAIL_CONFIRMATION=true
- [-] 13.10 Написать тест для отключения email confirmation если REQUIRE_EMAIL_CONFIRMATION=false

## 14. Database миграции и верификация

- [x] 14.1 Запустить миграции Alembic для применения изменений schema (если требуются)
- [x] 14.2 Проверить что unique constraints созданы в базе данных
- [x] 14.3 Проверить что email_confirmed field добавлен в User таблицу (если применимо)
- [x] 14.4 Проверить что index'ы созданы на email и username для performance
- [x] 14.5 Написать migration down script для отката в случае необходимости

## 15. Документация

- [-] 15.1 Обновить `docs/API.md` (если существует) с описанием новых endpoint'ов
- [-] 15.2 Добавить примеры успешной и неудачной регистрации в документацию
- [-] 15.3 Добавить примеры всех error response'ов (409, 422, 429)
- [-] 15.4 Добавить описание rate limiting в документацию
- [-] 15.5 Добавить описание email confirmation процесса если REQUIRE_EMAIL_CONFIRMATION=true
- [-] 15.6 Обновить README.md с информацией о регистрации пользователей

## 16. Локальное тестирование

- [-] 16.1 Запустить приложение локально с `uvicorn app.main:app --reload`
- [-] 16.2 Выполнить успешную регистрацию через curl/Postman и проверить response
- [-] 16.3 Проверить что email_confirmed флаг установлен правильно в базе данных
- [-] 16.4 Проверить что password хеширован (не сохранен в plaintext) в базе данных
- [-] 16.5 Проверить что пароль НЕ возвращается в response
- [-] 16.6 Протестировать дублирование email и получить 409 response
- [-] 16.7 Протестировать дублирование username и получить 409 response
- [-] 16.8 Если SUGGEST_USERNAMES=true, проверить suggestions в 409 response
- [-] 16.9 Протестировать rate limiting (11+ запросов в минуту должны получить 429)
- [-] 16.10 Проверить что Location header присутствует в 201 response

## 17. Audit логирование верификация

- [-] 17.1 Открыть database и проверить audit_logs таблицу после регистрации
- [-] 17.2 Убедиться что REGISTRATION_ATTEMPT_SUCCESS событие залогировано
- [-] 17.3 Убедиться что email и username сохранены в audit log
- [-] 17.4 Убедиться что user_id сохранен в audit log для успешной регистрации
- [-] 17.5 Убедиться что client_ip сохранен в audit log
- [-] 17.6 Убедиться что пароль НЕ сохранен в audit log
- [-] 17.7 Проверить дублирование email и убедиться что REGISTRATION_DUPLICATE_EMAIL событие залогировано
- [-] 17.8 Проверить дублирование username и убедиться что REGISTRATION_DUPLICATE_USERNAME событие залогировано

## 18. Load тестирование

- [-] 18.1 Написать load test script для rate limiter верификации
- [-] 18.2 Запустить 50+ параллельных регистрационных запросов на одном IP
- [-] 18.3 Убедиться что rate limiter корректно блокирует requests после лимита
- [-] 18.4 Проверить performance при высоком volume регистраций (database contention)
- [-] 18.5 Убедиться что система обрабатывает concurrent requests корректно (race conditions)

## 19. Email confirmation тестирование (если включено)

- [-] 19.1 Протестировать отправку confirmation email при регистрации
- [-] 19.2 Извлечь confirmation token из email и протестировать /confirm-email endpoint
- [-] 19.3 Убедиться что email_confirmed флаг обновляется после подтверждения
- [-] 19.4 Проверить что expired token'ы возвращают ошибку
- [-] 19.5 Проверить что invalid token'ы возвращают ошибку
- [-] 19.6 Проверить что пользователь может логиниться только после подтверждения (если требуется)

## 20. Backward compatibility верификация

- [x] 20.1 Убедиться что существующие auth endpoint'ы работают без изменений
- [x] 20.2 Убедиться что существующие user endpoints работают без изменений
- [x] 20.3 Убедиться что rate limiting для других endpoint'ов не изменились
- [x] 20.4 Убедиться что schema миграции не breaking для существующих данных
- [x] 20.5 Запустить все существующие тесты и убедиться что они passed

## 21. Security аудит

- [x] 21.1 Проверить что SQL injection защита работает (параметризованные запросы)
- [x] 21.2 Проверить что XSS защита работает для input fields
- [x] 21.3 Проверить что CORS настроена правильно (не слишком permissive)
- [x] 21.4 Убедиться что timing attack защита работает (одинаковое время ответа)
- [x] 21.5 Проверить что email enumeration атака затруднена через rate limiting
- [x] 21.6 Проверить что brute force атака защищена через rate limiting
- [x] 21.7 Убедиться что password безопасно хеширован (bcrypt, cost=12)
- [x] 21.8 Проверить что sensitive данные не логируются (пароли)

## 22. Deployment подготовка

- [x] 22.1 Убедиться что все environment переменные документированы в `.env.example`
- [x] 22.2 Убедиться что REGISTRATION_RATE_LIMIT значение установлено правильно для production
- [x] 22.3 Убедиться что REQUIRE_EMAIL_CONFIRMATION установлен правильно для production (обычно true)
- [x] 22.4 Убедиться что SMTP конфигурация установлена для production (если email confirmation требуется)
- [x] 22.5 Убедиться что AUDIT_LOG_RETENTION_DAYS установлен соответственно (GDPR compliance)
- [x] 22.6 Обновить Docker configuration если требуется (обычно не требуется)
- [x] 22.7 Убедиться что миграции будут применены автоматически при развертывании

## 23. Post-deployment верификация

- [-] 23.1 Проверить что endpoint доступен в production окружении
- [-] 23.2 Выполнить пробную регистрацию в production
- [-] 23.3 Проверить что audit logs создаются в production базе
- [-] 23.4 Проверить что rate limiting работает в production
- [-] 23.5 Проверить что email confirmation работает в production (если enabled)
- [-] 23.6 Проверить что все метрики и мониторинг работают корректно

## 24. Финальная проверка и документирование

- [-] 24.1 Запустить все unit и integration тесты
- [-] 24.2 Убедиться что code coverage достаточен (>80% для новых feature)
- [-] 24.3 Запустить linter и formatter (black, flake8, mypy)
- [-] 24.4 Проверить что нет security warnings в dependencies
- [-] 24.5 Обновить CHANGELOG с описанием новой feature
- [-] 24.6 Создать PR и получить code review
- [-] 24.7 Убедиться что все feedback from code review применен
- [-] 24.8 Выполнить final smoke тестирование перед merge
