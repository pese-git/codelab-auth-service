# Дизайн: Endpoint сброса пароля

**Версия:** 1.0.0  
**Дата:** 2026-03-24  
**Статус:** ✅ Design Document

---

## Context

### Текущее состояние

Сервис аутентификации имеет:
- FastAPI приложение с endpoints регистрации (`POST /api/v1/register`)
- SMTP интеграцию для отправки email (`add-smtp-integration` завершено)
- Систему email шаблонов для различных типов уведомлений
- Модель `email_confirmation_token` для подтверждения email адреса при регистрации
- SQLAlchemy ORM с асинхронным движком (AsyncSession)
- Систему rate limiting для защиты от brute-force атак

### Stakeholders

- **Пользователи**: Нужна возможность восстановить доступ при забывчивости пароля
- **Security team**: Требуется защита от перебора токенов и несанкционированного доступа
- **DevOps**: Нужна поддержка rate limiting и логирования без утечки sensitive данных
- **Админы**: Инструменты для отслеживания попыток восстановления и эскалации security проблем

### Constraints

- Интеграция с существующей SMTP инфраструктурой
- Использование существующего ORM (SQLAlchemy)
- Асинхронное выполнение всех операций (async/await)
- Безопасность - НЕ раскрывать информацию о существовании аккаунта в responses
- Performance - должно работать при нагрузке (rate limiting не должен блокировать сервис)

---

## Goals / Non-Goals

### Goals

1. **Безопасное восстановление пароля**: Позволить пользователям безопасно восстановить доступ через email верификацию
2. **Защита от abuse**: Реализовать rate limiting, защиту от brute-force, логирование suspicious активности
3. **User Experience**: Простой и понятный процесс восстановления с четкими инструкциями
4. **Privacy**: Не раскрывать информацию о существовании аккаунта в error messages
5. **Auditability**: Логирование всех операций для security анализа

### Non-Goals

- Двухфакторная аутентификация (2FA) - это отдельное изменение
- SMS отправка (только email)
- Обслуживание legacy пользователей без email - требуется email для recovery
- Полная audit trail с хранилищем (только логирование)
- Биометрическая аутентификация
- Поддержка federated identity recovery (OIDC recovery)

---

## Decisions

### Decision 1: Одноразовые токены со сроком действия вместо security questions

**Выбор**: Использовать криптографически стойкие одноразовые токены с 30-минутным сроком действия.

**Альтернативы**:
- Security questions (дата рождения, first pet name, etc.)
  - **Con**: Легко подбирать, пользователи часто не помнят свои ответы
- OTP (One-Time Passcode) через SMS
  - **Con**: Требует SMS API, дополнительные затраты, не всегда доступен
- OAuth provider recovery (Google, GitHub)
  - **Con**: Зависимость от external services, усложняет локальное deployment

**Rationale**: Одноразовые токены - стандарт industry для password recovery, криптографически безопасны, не требуют additional infrastructure.

**Implementation**: 
- Генерация: `secrets.token_urlsafe(32)` (рекомендуется OpenSSL в production)
- Хранение: SHA-256 хеш в БД (для защиты при компрометации)
- Срок действия: 30 минут (баланс между security и user experience)
- Одноразовость: Поле `used_at` в БД для отслеживания

---

### Decision 2: Две отдельные таблицы для модели vs. флаг в User таблице

**Выбор**: Создать отдельную таблицу `password_reset_tokens` (как `email_confirmation_token`)

**Альтернативы**:
- Добавить поля `reset_token_hash`, `reset_token_expires_at`, `reset_token_used_at` в таблицу `users`
  - **Con**: Усложняет User модель, смешивает concerns (authentication vs. recovery)
  - **Con**: Сложнее history/audit, нельзя иметь multiple pending tokens
- Redis для хранения токенов (in-memory)
  - **Con**: Дополнительная зависимость, требует Redis server, теряется при перезагрузке

**Rationale**: Отдельная таблица следует принципу SoC (Separation of Concerns), позволяет easy cleanup expired токенов, совместима с существующей pattern для `email_confirmation_token`.

**Implementation**:
```
CREATE TABLE password_reset_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  token_hash VARCHAR(64) NOT NULL UNIQUE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL DEFAULT NOW() + interval '30 minutes',
  used_at TIMESTAMP NULL,
  INDEX user_id,
  INDEX expires_at
)
```

---

### Decision 3: Rate limiting по user_id и по IP адресу

**Выбор**: Dual rate limiting - ограничение по user_id (3 requests/час) и по IP address (10 попыток подтверждения за 5 минут).

**Альтернативы**:
- Только по user_id
  - **Con**: Не защищает от distributed attacks (разные IP, один пользователь)
- Только по IP address
  - **Con**: Не защищает от targeted attacks (один атакующий может обойти одного пользователя, если он находится за NAT)
- Exponential backoff без hard limit
  - **Con**: Плохой UX для легитимных пользователей, сложно мониторить

**Rationale**: Комбинация двух методов - более надёжная защита, стандарт для auth систем.

**Implementation**: Использовать существующий rate limiter сервис (если есть) или добавить simple in-memory counter с TTL.

---

### Decision 4: Асинхронная отправка email через фоновую задачу

**Выбор**: Отправить email асинхронно, не блокировать endpoint response.

**Альтернативы**:
- Синхронная отправка в endpoint
  - **Con**: Slow endpoints (30+ sec), timeout если SMTP медленный
- Queue system (Celery, RQ, Bull)
  - **Con**: Additional infrastructure, operational complexity

**Rationale**: Асинхронная отправка email встроенным способом - баланс между reliability и complexity. Используем `asyncio.create_task()` или фоновые задачи FastAPI.

**Implementation**: 
```python
# В endpoint после создания токена:
background_tasks.add_task(send_password_reset_email, user.email, token)

# Или более надежно:
asyncio.create_task(password_reset_service.send_reset_email(user.email, token))
```

---

### Decision 5: Не раскрывать информацию о существовании аккаунта

**Выбор**: Вернуть одинаковый 200 response для существующих и несуществующих email адресов при запросе сброса.

**Альтернативы**:
- Вернуть 404 если пользователя нет
  - **Con**: Утечка информации о том, какие email зарегистрированы
- Вернуть 409 Conflict если уже есть активный reset token
  - **Con**: Позволяет атакующему перечислить валидные email

**Rationale**: Security best practice - не раскрывать информацию об аккаунтах потенциальным атакующим.

**Implementation**:
```python
@router.post("/password-reset/request")
async def request_password_reset(request: PasswordResetRequest):
    user = await user_service.get_by_email(request.email)
    if user:
        token = await password_reset_service.create_token(user.id)
        await send_password_reset_email_async(user.email, token)
    # Всегда возвращаем 200
    return {"message": "Check your email for reset instructions"}
```

---

### Decision 6: Валидация пароля - требования к сложности

**Выбор**: Пароль должен быть 8-64 символа с обязательным наличием: заглавных, строчных букв, цифр, спецсимволов.

**Альтернативы**:
- Просто минимум 8 символов (как в регистрации)
  - **Con**: Слабые пароли, low entropy
- Очень строгие требования (20+ символов, много спецсимволов)
  - **Con**: Плохой UX, сложно запомнить восстановленный пароль

**Rationale**: OWASP рекомендует 12+ символов ИЛИ комбинация типов символов. Выбрали комбинацию для баланса.

**Implementation**: Использовать `app/utils/validators.py` с существующей password validation логикой.

---

## Risks / Trade-offs

### Risk 1: Email delivery не гарантирована

**Описание**: Email может попасть в spam, не быть доставлен, или задержаться на часы.

**Mitigation**:
- Показать пользователю сообщение "Check spam folder" в UI
- Позволить повторить request (не более 3 раз в час)
- На будущее - добавить SMS/TOTP как альтернатива

**Trade-off**: Пользователь может временно потерять доступ если email не работает.

---

### Risk 2: Token brute-force если хеш скомпрометирован

**Описание**: Если таблица password_reset_tokens скомпрометирована (но не full hash inversion), атакующий может перебирать токены.

**Mitigation**:
- Rate limiting на IP - максимум 10 попыток за 5 минут
- Логирование всех failed attempts
- Мониторинг на surge в failed attempts
- Short expiration time - 30 минут (окно для brute-force ограничено)

**Trade-off**: Очень строгий rate limiting может заблокировать легитимных пользователей.

---

### Risk 3: Token sent in email может быть перехвачен

**Описание**: Email отправляется через открытый internet, может быть перехвачен или перенаправлен.

**Mitigation**:
- Всегда использовать HTTPS для reset links
- На production использовать verified SSL сертификаты
- Consider добавить IP validation в будущем (token valid только с IP который запросил reset)

**Trade-off**: Нельзя полностью защитить email канал, это inherent limitation.

---

### Risk 4: User забудет новый пароль сразу после сброса

**Описание**: UX: нет password recovery mechanism, только password reset.

**Mitigation**:
- Предложить пользователю "Remember me" option после успешного reset
- Session timeout более длительный после recovery
- Clear instructions при setup нового пароля

**Trade-off**: Все еще нужен полный password manager или возможность recovery, это out of scope для первой версии.

---

### Risk 5: Database migration с новой таблицей

**Описание**: Требуется миграция Alembic, может быть сложной в production.

**Mitigation**:
- Простая миграция (просто CREATE TABLE, без сложных constraints)
- Миграция обратима (DROP TABLE)
- Blue-green deployment для zero downtime (если необходимо)

**Trade-off**: Требуется координация с DevOps для deployment.

---

## Migration Plan

### Pre-deployment

1. **Prepare Alembic migration**:
   - Создать `migration/versions/20260324_xxxx_add_password_reset_tokens.py`
   - Миграция создаёт таблицу `password_reset_tokens` с индексами
   - Тестировать migration на staging environment

2. **Code review и testing**:
   - Unit tests для всех компонентов
   - Integration tests для полного flow
   - Load testing на rate limiting

3. **Configuration**:
   - Убедиться что SMTP configured и работает
   - Настроить rate limit параметры (3 requests/hour, 10 attempts/5min)
   - Подготовить email шаблоны (уже существуют в проекте)

### Deployment

1. **Blue-green или rolling deployment**:
   - Deploy новый код (endpoints готовы обслуживать requests)
   - Run Alembic migration (создаёт таблицу)
   - Endpoints доступны после миграции

2. **Monitoring**:
   - Мониторить error logs для password reset endpoints
   - Мониторить email delivery rate
   - Alert на surge в failed attempts (brute-force protection)

### Post-deployment

1. **Testing в production** (limited rollout):
   - Пригласить test users для testing полного flow
   - Проверить email delivery в production SMTP

2. **Documentation**:
   - Обновить API документацию
   - Добавить user guide в FAQ

3. **Monitoring и maintenance**:
   - Daily check email delivery logs
   - Weekly cleanup старых используемых токенов (cleanup job)
   - Monthly review security logs

### Rollback strategy

Если возникнут критические проблемы:
1. Отключить endpoints в code (return 503 Service Unavailable)
2. Миграция **обратима** - можно DROP TABLE password_reset_tokens
3. Старый код может работать без этого feature (graceful degradation)

---

## Open Questions

1. **Redis vs. In-memory для rate limiting?**
   - Текущий выбор: In-memory counter с TTL
   - Question: Нужен ли Redis для distributed rate limiting если есть несколько instances?
   - Action: Решить в зависимости от deployment topology

2. **Email template локализация?**
   - Question: Отправлять письмо на языке пользователя или на English?
   - Action: Проверить существующую систему email шаблонов, текущая language preference в User модели

3. **Cleanup expired токенов?**
   - Question: Активное удаление старых токенов или ленивое удаление при access?
   - Action: Реализовать background job для cleanup если нужно (scheduled task)

4. **Audit logging?**
   - Question: Логировать в какую систему? (файл, database, external logging service)
   - Action: Использовать существующую audit service (`app/services/audit_service.py`)

---

## Testing Strategy

### Unit Tests
- Token generation: правильный формат, entropy
- Token hashing: детерминизм, security
- Rate limiting: counter increment, reset
- Password validation: требования к сложности
- Email template rendering: переменные substitution

### Integration Tests
- Полный flow: request → email → confirm → success
- Error cases: expired token, invalid token, weak password
- Rate limiting: должно блокировать после лимита
- Email sending: mock SMTP, проверить calls

### Load Tests
- Rate limiting при 1000+ requests
- Database queries performance (индексы на user_id, expires_at)

---

## Future Improvements

1. **Email backup codes** - альтернатива для пользователей без доступа к email
2. **SMS OTP** - SMS как backup или primary channel
3. **TOTP/2FA** - двухфакторная аутентификация
4. **Device fingerprinting** - более точная защита от brute-force
5. **Password strength meter** - UI для показа требований при вводе нового пароля
6. **Federated recovery** - recovery через Google/GitHub если configured
