# SMTP Integration Спецификация

**Версия:** 1.0.0  
**Статус:** ✅ New Capability  
**Дата:** 2026-03-23

---

## 📋 Обзор

Интеграция асинхронной библиотеки `aiosmtplib` для фактической отправки email через SMTP сервер с поддержкой аутентификации, TLS шифрования и обработкой ошибок соединения.

---

## ADDED Requirements

### Requirement: Асинхронная отправка email через SMTP

Система ДОЛЖНА предоставить механизм отправки email через SMTP сервер в асинхронном режиме с поддержкой TLS/SSL шифрования и базовой аутентификации.

#### Scenario: Успешная отправка email с TLS
- **WHEN** приложение инициирует отправку email на валидный адрес через аутентифицированное SMTP соединение с TLS
- **THEN** email успешно отправляется и функция возвращает `True`

#### Scenario: Отправка email без TLS
- **WHEN** приложение инициирует отправку email на SMTP сервер с `smtp_use_tls=False`
- **THEN** email отправляется без шифрования, используется открытое соединение

#### Scenario: Ошибка соединения с SMTP сервером
- **WHEN** SMTP сервер недоступен (SMTPServerError, ConnectionError)
- **THEN** исключение логируется без раскрытия деталей пользователю, функция возвращает `False`

#### Scenario: Ошибка аутентификации SMTP
- **WHEN** учетные данные SMTP некорректны (SMTPAuthenticationError)
- **THEN** ошибка логируется как критическая, функция возвращает `False`, требуется проверка конфигурации

#### Scenario: Таймаут соединения SMTP
- **WHEN** SMTP сервер не отвечает в течение timeout (default 30 сек)
- **THEN** соединение прерывается, ошибка логируется, функция возвращает `False`

### Requirement: Интеграция с конфигурацией

Система ДОЛЖНА использовать SMTP параметры из конфигурации приложения для всех операций отправки email.

#### Scenario: Загрузка SMTP параметров из переменных окружения
- **WHEN** приложение инициализируется с переменными окружения `AUTH_SERVICE__SMTP_HOST`, `AUTH_SERVICE__SMTP_PORT`, `AUTH_SERVICE__SMTP_USERNAME`, `AUTH_SERVICE__SMTP_PASSWORD`, `AUTH_SERVICE__SMTP_FROM_EMAIL`
- **THEN** все параметры корректно загружаются в Settings и доступны для использования

#### Scenario: Значения по умолчанию для SMTP параметров
- **WHEN** переменные окружения SMTP не установлены
- **THEN** система использует значения по умолчанию: smtp_host="localhost", smtp_port=587, smtp_use_tls=True, smtp_from_email="noreply@codelab.local"

#### Scenario: Отправка email с указанным From адресом
- **WHEN** email отправляется через SMTP
- **THEN** письмо содержит From адрес из `smtp_from_email`, полученный из конфигурации

### Requirement: Обработка ошибок и логирование

Система ДОЛЖНА корректно обрабатывать различные сценарии ошибок SMTP и логировать их без раскрытия чувствительной информации в логах.

#### Scenario: Логирование успешной отправки
- **WHEN** email успешно отправляется
- **THEN** событие логируется на уровне INFO с указанием recipient и message_id

#### Scenario: Логирование ошибок без credentials
- **WHEN** происходит ошибка SMTP
- **THEN** логируется только тип ошибки и сообщение, НЕ логируются credentials или полный stack trace в production

#### Scenario: Graceful fallback при недоступности SMTP
- **WHEN** SMTP сервер недоступен и email не может быть отправлен
- **THEN** функция возвращает `False` для graceful degradation, позволяя API продолжить работу

---

## Constraints

- **Асинхронность**: Все операции SMTP должны быть асинхронными (async/await) для неблокирующего выполнения
- **Таймаут**: Максимальное время ожидания SMTP ответа - 30 секунд (configurable)
- **Безопасность**: Credentials НЕ должны логироваться или передаваться в явном виде
- **TLS/SSL**: При использовании TLS должен быть STARTTLS для port 587 или SSL для port 465
- **Rate Limiting**: Отправка email может быть ограничена в application logic на основе пользователя
- **Отправка из одного адреса**: Система отправляет email только из адреса `smtp_from_email`

---

## Dependencies

- **Зависит от**: `email-templates` (требуется подготовленное письмо с content)
- **Зависит от**: `configuration` (SMTP параметры из settings)
- **Используется в**: `email-notifications` (фактическая отправка уведомлений)
- **Используется в**: `email-retry-logic` (retry механизм вызывает эту функцию)

---

## Testing

### Unit Tests

1. **test_send_email_success_with_tls**
   - Mock aiosmtplib, имитировать успешное соединение
   - Проверить, что функция возвращает True
   - Проверить, что вызваны методы SMTP: starttls(), login(), sendmail()

2. **test_send_email_without_tls**
   - Отправка с `smtp_use_tls=False`
   - Проверить, что starttls() НЕ вызывается
   - Проверить успешное выполнение

3. **test_send_email_smtp_authentication_error**
   - Mock aiosmtplib с SMTPAuthenticationError
   - Проверить возврат False
   - Проверить логирование ошибки

4. **test_send_email_connection_error**
   - Mock aiosmtplib с ConnectionError
   - Проверить возврат False
   - Проверить graceful обработку

5. **test_send_email_timeout**
   - Mock с asyncio.TimeoutError
   - Проверить обработку timeout
   - Проверить логирование

6. **test_smtp_configuration_from_settings**
   - Проверить загрузку параметров из Settings
   - Проверить, что все параметры корректно передаются в SMTP

### Integration Tests

1. **test_send_email_with_mock_smtp_server**
   - Использовать fake-smtp-server или MailHog
   - Отправить реальный email
   - Проверить получение письма на mock сервере

2. **test_send_email_with_invalid_recipient**
   - Попытка отправить на невалидный email
   - Проверить обработку ошибки SMTP

### Security Tests

1. **test_no_credentials_in_logs**
   - Отправить email и проанализировать логи
   - Проверить отсутствие password в логах

2. **test_tls_encryption_enabled**
   - Проверить что TLS включается при smtp_use_tls=True
   - Проверить что SSL используется для port 465

---

## Implementation Notes

- Использовать `aiosmtplib` для асинхронной работы с SMTP
- Создать класс `SMTPEmailSender` в `app/services/email_sender.py`
- Интегрировать в существующий `EmailService` или создать отдельный сервис
- Все ошибки должны быть перехвачены и обработаны gracefully
- Логирование должно быть информативным, но безопасным
