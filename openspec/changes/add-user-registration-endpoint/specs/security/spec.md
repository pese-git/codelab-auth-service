# Спецификация безопасности - Delta

**Версия:** 1.0.0  
**Статус:** Modified  
**Дата:** 2026-03-22

---

## MODIFIED Requirements

### Requirement: Rate limiting для публичного endpoint регистрации
Система ДОЛЖНА защитить endpoint регистрации от abuse через rate limiting по IP адресу, интегрируясь с существующим RateLimiter middleware.

**Модифицировано:** Расширение существующей спецификации rate limiting с добавлением более строгих ограничений для публичного endpoint регистрации.

**Конфигурация:**
- Rate limit для /api/v1/register: 10 request'ов в минуту на IP адрес
- Параметр конфигурации: `REGISTRATION_RATE_LIMIT` (по-умолчанию: 10)
- Применяется на middleware уровне перед бизнес логикой

#### Scenario: Rate limit не превышен
- **WHEN** клиент отправляет 5 регистраций в течение одной минуты
- **THEN** все запросы обрабатываются успешно

#### Scenario: Rate limit превышен
- **WHEN** клиент отправляет 11 регистраций в течение одной минуты
- **THEN** 11-я request возвращает 429 Too Many Requests

#### Scenario: Rate limit response содержит Retry-After
- **WHEN** клиент превышает rate limit
- **THEN** response содержит Retry-After header с временем в секундах

#### Scenario: Rate limit счётчик сбрасывается
- **WHEN** одна минута прошла после первого запроса
- **THEN** счётчик сбрасывается и клиент может отправить новые запросы

#### Scenario: Rate limit по IP адресу, не по username
- **WHEN** клиент регистрирует 10 разных аккаунтов с одного IP
- **THEN** 11-я попытка блокируется (rate limit по IP, не по username)

#### Scenario: Разные IP адреса имеют отдельные лимиты
- **WHEN** клиент A с IP1 отправляет 10 запросов, клиент B с IP2 отправляет запрос
- **THEN** клиент B получает успешный ответ (отдельный лимит для каждого IP)

### Requirement: Защита от enumeration атак
Система ДОЛЖНА защищать от enumeration атак, которые позволяют злоумышленнику перечислить существующие email адреса в системе.

**Модифицировано:** Расширение спецификации валидации с добавлением требований защиты от enumeration.

#### Scenario: Одинаковое время ответа для существующего и несуществующего email
- **WHEN** клиент регистрируется с существующим email
- **THEN** время ответа примерно одинаково с временем для новых email (из-за хеширования пароля)

#### Scenario: Не раскрывается информация о существовании email
- **WHEN** клиент получает 409 error для дублирования email
- **THEN** error message не раскрывает информацию об existing user (только "Email already registered")

#### Scenario: Логирование дублирования не влияет на response
- **WHEN** клиент пытается зарегистрировать существующий email
- **THEN** event логируется в audit_logs но response message одинаковый для всех validation ошибок

### Requirement: Валидация пароля на безопасность
Система ДОЛЖНА валидировать пароль на минимальную длину (8 символов) согласно спецификации User Registration.

**Модифицировано:** Расширение требований валидации пароля.

#### Scenario: Минимальная длина пароля 8 символов
- **WHEN** клиент регистрируется с паролем "Pass123" (7 символов)
- **THEN** система возвращает 422 Unprocessable Entity

#### Scenario: Пароль 8 символов допускается
- **WHEN** клиент регистрируется с паролем "Pass1234" (8 символов)
- **THEN** пароль валидируется успешно

#### Scenario: Пароль хешируется перед сохранением
- **WHEN** пароль валидируется и сохраняется
- **THEN** в БД сохраняется только bcrypt хеш, не сам пароль

### Requirement: Audit logging для регистрации
Система ДОЛЖНА логировать все события регистрации для обеспечения аудита и обнаружения атак.

**Модифицировано:** Расширение audit logging требований с добавлением специфичных событий для регистрации.

**События логирования:**
- `REGISTRATION_ATTEMPT_SUCCESS`: Успешная регистрация
- `REGISTRATION_ATTEMPT_FAILED`: Неудачная попытка регистрации
- `REGISTRATION_DUPLICATE_EMAIL`: Попытка дублирования email
- `REGISTRATION_DUPLICATE_USERNAME`: Попытка дублирования username

#### Scenario: REGISTRATION_ATTEMPT_SUCCESS событие
- **WHEN** пользователь успешно регистрируется
- **THEN** в audit_logs создается запись с event_type=REGISTRATION_ATTEMPT_SUCCESS, email, username, user_id, client_ip, timestamp

#### Scenario: REGISTRATION_ATTEMPT_FAILED событие
- **WHEN** пользователь не проходит валидацию (слабый пароль, невалидный email)
- **THEN** в audit_logs создается запись с event_type=REGISTRATION_ATTEMPT_FAILED, email, username, failure_reason, client_ip, timestamp

#### Scenario: REGISTRATION_DUPLICATE_EMAIL событие
- **WHEN** пользователь пытается зарегистрировать существующий email
- **THEN** в audit_logs создается запись с event_type=REGISTRATION_DUPLICATE_EMAIL, attempted_email, existing_user_id

#### Scenario: REGISTRATION_DUPLICATE_USERNAME событие
- **WHEN** пользователь пытается зарегистрировать существующий username
- **THEN** в audit_logs создается запись с event_type=REGISTRATION_DUPLICATE_USERNAME, attempted_username, existing_user_id

#### Scenario: Логирование содержит IP адрес клиента
- **WHEN** пользователь регистрируется
- **THEN** audit log запись содержит client_ip адрес для отслеживания источника

#### Scenario: Логирование содержит user_agent
- **WHEN** пользователь регистрируется
- **THEN** audit log запись содержит user_agent (если доступен) для отслеживания клиента

#### Scenario: Не логируются пароли
- **WHEN** пользователь регистрируется
- **THEN** audit log запись НЕ содержит пароль или его хеш

### Requirement: SQL Injection защита при проверке дублирования
Система ДОЛЖНА использовать параметризованные запросы при проверке уникальности email и username.

#### Scenario: Параметризованные запросы для проверки email
- **WHEN** система проверяет существование email "user' OR '1'='1"
- **THEN** используется параметризованный запрос (SQLAlchemy ORM), не прямое конкатенирование

#### Scenario: Параметризованные запросы для проверки username
- **WHEN** система проверяет существование username "admin'; DROP TABLE users; --"
- **THEN** используется параметризованный запрос, SQL injection предотвращена

### Requirement: Защита от race condition при дублировании
Система ДОЛЖНА использовать database constraint для защиты от race condition когда две request'ы одновременно пытаются создать с одинаковым email или username.

#### Scenario: Database unique constraint на email
- **WHEN** две request'ы одновременно пытаются создать пользователя с одинаковым email
- **THEN** database constraint предотвращает дублирование, одна request успешна, другая получает constraint violation

#### Scenario: Database unique constraint на username
- **WHEN** две request'ы одновременно пытаются создать пользователя с одинаковым username
- **THEN** database constraint предотвращает дублирование, одна request успешна, другая получает constraint violation

#### Scenario: Обработка constraint violation
- **WHEN** database возвращает constraint violation ошибку
- **THEN** приложение преобразует это в 409 Conflict с корректным error message

---

## ADDED Requirements

### Requirement: Защита от brute force на публичном endpoint
Система ДОЛЖНА использовать rate limiting для защиты от brute force атак на публичном endpoint регистрации.

#### Scenario: Защита от массовой регистрации фейковых аккаунтов
- **WHEN** злоумышленник пытается зарегистрировать 100 фейковых аккаунтов с одного IP
- **THEN** после 10 регистраций в минуту, остальные запросы блокируются с 429 Too Many Requests

#### Scenario: Защита от перебора username/email
- **WHEN** злоумышленник пытается перечислить существующие username/email через неудачные попытки
- **THEN** rate limiting и timing attack защита предотвращают быструю перечисление

