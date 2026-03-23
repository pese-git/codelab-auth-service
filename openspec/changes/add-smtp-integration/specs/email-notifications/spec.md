# Email Notifications Спецификация

**Версия:** 1.0.0  
**Статус:** ✅ New Capability  
**Дата:** 2026-03-23

---

## 📋 Обзор

Система отправки email-уведомлений при важных событиях в системе аутентификации (регистрация пользователя, подтверждение email, сброс пароля). Интегрируется с регистрационным flow и использует email-templates для рендеринга и smtp-integration для отправки.

---

## ADDED Requirements

### Requirement: Отправка email при регистрации

Система ДОЛЖНА отправлять приветственное письмо при успешной регистрации нового пользователя.

#### Scenario: Отправка welcome email после успешной регистрации
- **WHEN** пользователь успешно регистрируется (POST /api/v1/register возвращает 201)
- **THEN** система отправляет welcome email на указанный email адрес с именем пользователя

#### Scenario: Welcome email содержит корректные данные
- **WHEN** welcome email отправляется после регистрации
- **THEN** письмо содержит: username пользователя, email адрес, дату регистрации, ссылку на профиль

#### Scenario: Ошибка отправки email не прерывает регистрацию
- **WHEN** SMTP недоступен во время отправки welcome email
- **THEN** регистрация завершается успешно (201 возвращается), email логируется как невыполненный

#### Scenario: Email отправляется асинхронно
- **WHEN** пользователь регистрируется
- **THEN** welcome email отправляется в фоновом процессе, не блокируя API ответ

### Requirement: Отправка email подтверждения

Система ДОЛЖНА отправлять email с ссылкой подтверждения для верификации email адреса (если require_email_confirmation=True).

#### Scenario: Отправка confirmation email после регистрации
- **WHEN** пользователь регистрируется и require_email_confirmation=True
- **THEN** система отправляет confirmation email с уникальной ссылкой подтверждения

#### Scenario: Confirmation email содержит токен
- **WHEN** confirmation email отправляется
- **THEN** письмо содержит: username, ссылка с токеном подтверждения, время истечения токена (обычно 24 часа)

#### Scenario: Токен подтверждения валиден только один раз
- **WHEN** пользователь кликает на ссылку подтверждения в письме
- **THEN** email подтверждается, флаг email_confirmed устанавливается в True

#### Scenario: Повторная отправка confirmation email
- **WHEN** пользователь запрашивает повторную отправку confirmation email
- **THEN** генерируется новый токен, отправляется новое письмо со свежей ссылкой

#### Scenario: Expired confirmation token
- **WHEN** пользователь пытается подтвердить email с истекшим токеном
- **THEN** система возвращает ошибку с указанием что токен истек, предлагает запросить новое письмо

### Requirement: Отправка email сброса пароля

Система ДОЛЖНА отправлять email с ссылкой сброса пароля при запросе пользователя (если потребуется в будущем).

#### Scenario: Отправка password reset email
- **WHEN** пользователь запрашивает сброс пароля (POST /api/v1/password-reset)
- **THEN** система отправляет password reset email с уникальной ссылкой сброса

#### Scenario: Password reset email содержит правильный контент
- **WHEN** password reset email отправляется
- **THEN** письмо содержит: username, ссылка со временем действия, инструкции по сбросу

#### Scenario: Защита от brute force при сбросе пароля
- **WHEN** система отправляет много password reset email одному пользователю
- **THEN** применяется rate limiting для предотвращения спама

### Requirement: Управление типами уведомлений

Система ДОЛЖНА предоставить механизм для управления какие типы email отправляются и в каких условиях.

#### Scenario: Конфигурация включения/отключения типов уведомлений
- **WHEN** в конфигурации установлено `send_welcome_email=True/False`
- **THEN** welcome email отправляется/не отправляется при регистрации

#### Scenario: Конфигурация обязательности подтверждения email
- **WHEN** в конфигурации установлено `require_email_confirmation=True/False`
- **THEN** confirmation email отправляется/не отправляется в зависимости от конфига

#### Scenario: Предпочтения пользователя по уведомлениям
- **WHEN** пользователь устанавливает preferences для email уведомлений
- **THEN** система уважает эти preferences и не отправляет нежелательные письма

### Requirement: Обработка невалидных email адресов

Система ДОЛЖНА корректно обрабатывать случаи отправки на невалидные email адреса.

#### Scenario: Невалидный email адрес при регистрации
- **WHEN** пользователь регистрируется с невалидным email (должен быть предотвращен на уровне валидации)
- **THEN** регистрация отклоняется перед отправкой email

#### Scenario: Bounced email логируется
- **WHEN** SMTP сервер возвращает ошибку "user not found" или "mailbox full"
- **THEN** ошибка логируется, может быть отмечена для дальнейшей обработки

### Requirement: Логирование событий email

Система ДОЛЖНА логировать все события отправки email для аудита и отладки.

#### Scenario: Успешная отправка логируется
- **WHEN** email успешно отправляется
- **THEN** логируется событие с типом письма, адресатом, timestamp

#### Scenario: Неудача отправки логируется
- **WHEN** email не удается отправить
- **THEN** логируется событие с типом ошибки, адресатом, рекомендация по исправлению

---

## Constraints

- **Асинхронность**: Email должны отправляться асинхронно, не блокируя API ответы
- **Надежность**: Ошибки отправки НЕ должны прерывать основные операции (регистрация, сброс пароля)
- **Приватность**: Email адреса НЕ должны логироваться в полном виде в публичные логи
- **Rate Limiting**: Отправка email на один адрес должна быть ограничена (max N писем в час)
- **Template**: Все письма должны использовать шаблоны из email-templates
- **From Address**: Все письма отправляются из smtp_from_email, указанного в конфигурации
- **Timeout**: Если email не отправляется в течение разумного времени, операция должна таймауться
- **Retry**: Неудачные попытки отправки обрабатываются механизмом retry (см. email-retry-logic)

---

## Dependencies

- **Зависит от**: `smtp-integration` (использует SMTP для фактической отправки)
- **Зависит от**: `email-templates` (использует шаблоны для рендеринга писем)
- **Зависит от**: `email-retry-logic` (неудачные попытки передаются в retry механизм)
- **Модифицирует**: `registration-flow` (отправляет email при успешной регистрации)
- **Используется в**: `app/api/v1/register.py` (отправка welcome и confirmation emails)

---

## Testing

### Unit Tests

1. **test_send_welcome_email_on_registration**
   - Mock EmailService и SMTP
   - Создать пользователя через сервис
   - Проверить что send_welcome_email вызывается

2. **test_welcome_email_contains_username**
   - Отправить welcome email для пользователя "john_doe"
   - Проверить что в email теле содержится "john_doe"

3. **test_registration_succeeds_even_if_email_fails**
   - Mock SMTP с ошибкой
   - Создать пользователя
   - Проверить что пользователь создан несмотря на ошибку email

4. **test_send_confirmation_email_on_registration**
   - require_email_confirmation=True
   - Создать пользователя
   - Проверить что confirmation email отправляется

5. **test_confirmation_email_contains_token**
   - Отправить confirmation email
   - Проверить что письмо содержит токен подтверждения

6. **test_send_password_reset_email**
   - Вызвать функцию сброса пароля
   - Проверить что password reset email отправляется

7. **test_password_reset_email_contains_link**
   - Отправить password reset email
   - Проверить что письмо содержит уникальную ссылку сброса

8. **test_email_notification_config_respected**
   - Установить send_welcome_email=False
   - Создать пользователя
   - Проверить что welcome email НЕ отправляется

9. **test_invalid_email_not_sent**
   - Попытка отправить email на невалидный адрес
   - Проверить что email не отправляется

10. **test_email_event_logged**
    - Отправить email
    - Проверить что события логируются

### Integration Tests

1. **test_welcome_email_integration_with_smtp**
    - Использовать real или mock SMTP сервер
    - Создать пользователя
    - Проверить что письмо получено на SMTP сервере

2. **test_confirmation_flow_end_to_end**
    - Создать пользователя
    - Получить confirmation email
    - Извлечь токен из письма
    - Подтвердить email через API
    - Проверить что email_confirmed установлен в True

3. **test_multiple_confirmation_emails**
    - Запросить повторную отправку confirmation email
    - Проверить что новое письмо содержит новый токен

4. **test_expired_confirmation_token**
    - Получить confirmation email
    - Дождаться истечения токена (или мок время)
    - Попытаться подтвердить
    - Проверить ошибку об истечении

### Async Tests

1. **test_email_sent_asynchronously**
    - Отправить email
    - Проверить что функция возвращает контроль быстро
    - Проверить что email все равно отправляется в фоне

### Rate Limiting Tests

1. **test_email_rate_limiting_per_user**
    - Попытаться отправить много email одному пользователю
    - Проверить что rate limiting срабатывает после N писем

---

## Implementation Notes

- Создать класс `EmailNotificationService` в `app/services/email_notifications.py`
- Использовать асинхронные функции для всех операций
- Интегрировать с существующим `EmailService` в `app/services/email_service.py`
- Реализовать отправку в background через asyncio.create_task() или очередь
- Логировать все события в audit log
- Использовать DatabaseSession для записи истории отправленных emails (если требуется)
- Добавить переменные конфигурации в `app/core/config.py` для управления типами уведомлений
