# Email Retry Logic Спецификация

**Версия:** 1.0.0  
**Статус:** ✅ New Capability  
**Дата:** 2026-03-23

---

## 📋 Обзор

Механизм повтора отправки email при временных ошибках соединения с SMTP сервером. Обеспечивает надежность доставки писем с использованием exponential backoff стратегии и ограничением количества попыток.

---

## ADDED Requirements

### Requirement: Автоматический retry при ошибках SMTP

Система ДОЛЖНА автоматически повторять попытки отправки email при временных ошибках (timeout, connection refused, temp server errors).

#### Scenario: Retry при SMTPServerError
- **WHEN** SMTP сервер временно недоступен (SMTPServerError с кодом 4xx)
- **THEN** система автоматически повторяет отправку через 5 секунд

#### Scenario: Retry при timeout
- **WHEN** соединение SMTP истекает (asyncio.TimeoutError)
- **THEN** система повторяет отправку с новой попыткой

#### Scenario: Retry при ConnectionError
- **WHEN** невозможно установить соединение с SMTP сервером
- **THEN** система повторяет попытку соединения

#### Scenario: No retry на постоянные ошибки
- **WHEN** SMTP сервер возвращает постоянную ошибку (SMTPServerError с кодом 5xx, например "user not found")
- **THEN** система НЕ повторяет отправку, логирует ошибку как критическую

#### Scenario: No retry на ошибки аутентификации
- **WHEN** SMTP аутентификация не удается (SMTPAuthenticationError)
- **THEN** система НЕ повторяет, логирует как критическую ошибку конфигурации

### Requirement: Exponential Backoff стратегия

Система ДОЛЖНА использовать exponential backoff с полученными приращениями для избежания перегрузки SMTP сервера при множественных повторных попытках.

#### Scenario: Первая попытка retry
- **WHEN** первая отправка не удается
- **THEN** система ожидает 5 секунд перед повторной попыткой (base_delay=5s)

#### Scenario: Вторая попытка retry
- **WHEN** первая повторная попытка не удается
- **THEN** система ожидает 10 секунд перед следующей попыткой (5s * 2^1)

#### Scenario: Третья попытка retry
- **WHEN** вторая повторная попытка не удается
- **THEN** система ожидает 20 секунд перед следующей попыткой (5s * 2^2)

#### Scenario: Maximum backoff cap
- **WHEN** exponential backoff превышает максимум (max_backoff=300s, 5 минут)
- **THEN** система не увеличивает delay свыше 300 секунд

#### Scenario: Jitter для избежания thundering herd
- **WHEN** delay рассчитывается для retry
- **THEN** к delay добавляется случайный jitter (±10%) для избежания синхронного retry множества email

### Requirement: Ограничение количества попыток

Система ДОЛЖНА ограничивать максимальное количество повторных попыток для избежания бесконечных retry циклов.

#### Scenario: Максимум 3 попытки
- **WHEN** email не удается отправить
- **THEN** система повторяет максимум 3 раза (итого 4 попытки: 1 оригинальная + 3 retry)

#### Scenario: Превышение максимума попыток
- **WHEN** все 3 retry попытки исчерпаны без успеха
- **THEN** система отмечает email как "failed", логирует как ошибку, может отправить уведомление администратору

#### Scenario: Конфигурируемое количество retry
- **WHEN** в конфигурации установлено `smtp_max_retries=5`
- **THEN** система использует это значение вместо значения по умолчанию

### Requirement: Хранение истории попыток

Система ДОЛЖНА сохранять информацию о каждой попытке отправки для аудита и отладки.

#### Scenario: Логирование каждой попытки
- **WHEN** система повторяет отправку email
- **THEN** логируется информация: номер попытки, тип ошибки, время следующей попытки

#### Scenario: История попыток в логах
- **WHEN** email отправляется после нескольких retry попыток
- **THEN** в логах присутствует полная история: исходная попытка + все retry попытки

#### Scenario: Отметка о статусе доставки
- **WHEN** email успешно доставляется после retry
- **THEN** статус устанавливается в "delivered", отмечается успех после N попыток

#### Scenario: Отметка о неудачной доставке
- **WHEN** email не удается доставить после всех retry попыток
- **THEN** статус устанавливается в "failed", отмечается исчерпание попыток

### Requirement: Интеграция с очередью или background job системой

Система ДОЛЖНА поддерживать выполнение retry попыток через background job систему (например, Redis queue, Celery или встроенный asyncio scheduler).

#### Scenario: Retry через asyncio scheduler
- **WHEN** требуется повторная отправка
- **THEN** система планирует async задачу на повторную отправку после delay

#### Scenario: Retry после перезагрузки приложения
- **WHEN** приложение перезагружается во время retry цикла
- **THEN** неотправленные email остаются в очереди и переотправляются при следующем запуске

#### Scenario: Persistance retry queue
- **WHEN** email в очереди retry
- **THEN** информация о email сохраняется в БД или persistent queue для восстановления после краша

#### Scenario: Выполнение retry в фоне
- **WHEN** retry для email запланирован
- **THEN** retry выполняется асинхронно, не блокируя основной процесс

### Requirement: Мониторинг и оповещение

Система ДОЛЖНА предоставить видимость в статус retry процесса и оповещать об аномалиях.

#### Scenario: Метрики retry попыток
- **WHEN** система обрабатывает email с retry
- **THEN** собираются метрики: количество retry попыток, success rate, failed emails

#### Scenario: Оповещение при постоянных сбоях
- **WHEN** множество email не удается доставить (например, >10% от отправок)
- **THEN** система может отправить alert администратору

#### Scenario: Dashboard/logs для мониторинга
- **WHEN** администратор проверяет логи
- **THEN** видит статистику: сколько email в retry, сколько failed, тренды доставки

---

## Constraints

- **Максимум retry**: 3 повторных попытки (configurable)
- **Base delay**: 5 секунд между попытками (configurable)
- **Max backoff**: 300 секунд (5 минут) максимум между попытками
- **Exponential factor**: 2.0 (каждая следующая попытка откладывается в 2 раза дольше)
- **Jitter**: ±10% случайности для избежания thundering herd
- **Только временные ошибки**: Retry только для временных ошибок (4xx коды), не для постоянных (5xx)
- **История**: Вся история retry должна логироваться
- **Async**: Все retry операции должны быть асинхронными
- **Graceful degradation**: Если retry система недоступна, email отправляется с максимум 1 попыткой

---

## Dependencies

- **Зависит от**: `smtp-integration` (повторяет вызов функции отправки SMTP)
- **Зависит от**: `email-notifications` (обрабатывает неудачные попытки из notifications)
- **Зависит от**: `configuration` (smtp_max_retries параметры из конфига)
- **Требует**: AsyncIO или аналогичной системы для планирования задач
- **Опционально**: Redis/Celery для persistent retry queue (если требуется)

---

## Testing

### Unit Tests

1. **test_retry_on_smtp_server_error**
   - Mock SMTP с SMTPServerError на первой попытке, успех на второй
   - Проверить что система повторяет
   - Проверить что email отправляется

2. **test_no_retry_on_permanent_error**
   - Mock SMTP с SMTPServerError 550 (постоянная ошибка)
   - Проверить что система НЕ повторяет
   - Проверить логирование как failed

3. **test_no_retry_on_authentication_error**
   - Mock SMTP с SMTPAuthenticationError
   - Проверить что система НЕ повторяет
   - Проверить логирование как критическая ошибка

4. **test_exponential_backoff_calculation**
   - Вычислить delay для retry 1, 2, 3
   - Проверить: 5s, 10s, 20s

5. **test_exponential_backoff_max_cap**
   - Вычислить delay для retry 10
   - Проверить что delay не превышает 300s

6. **test_jitter_in_backoff**
   - Вычислить delay с jitter
   - Проверить что результат в диапазоне ±10% от базового

7. **test_max_retry_attempts**
   - Попытаться отправить email с max_retries=3
   - Мок SMTP чтобы всегда возвращал ошибку
   - Проверить что попыток ровно 4 (1 оригинальная + 3 retry)

8. **test_success_on_second_retry**
   - Мок SMTP: ошибка, ошибка, успех
   - Проверить что email отправляется на 3-й попытке

9. **test_retry_history_logged**
   - Отправить email с retry
   - Проверить что логи содержат информацию о каждой попытке

10. **test_status_delivered_after_retry**
    - Email отправляется на 2-й попытке
    - Проверить что статус "delivered"

11. **test_status_failed_after_max_retries**
    - Все retry попытки исчерпаны
    - Проверить что статус "failed"

### Integration Tests

1. **test_retry_with_mock_smtp_timeout**
    - Mock SMTP с первым timeout, затем успех
    - Проверить что retry срабатывает после timeout

2. **test_retry_with_connection_error**
    - Mock с первым ConnectionError, потом успех
    - Проверить восстановление

3. **test_multiple_emails_retry_independently**
    - Отправить 3 email с разными ошибками
    - Проверить что каждое имеет свой retry цикл

4. **test_retry_queue_persistence**
    - Поместить email в retry queue
    - Проверить что он присутствует в очереди
    - Получить из очереди - проверить данные

### Async/Timing Tests

1. **test_retry_delay_respected**
    - Отправить email с retry на первой попытке
    - Измерить время до второй попытки
    - Проверить что задержка соответствует base_delay

2. **test_async_retry_execution**
    - Отправить email с retry
    - Проверить что функция возвращает контроль быстро
    - Проверить что retry все равно выполняется

### Configuration Tests

1. **test_custom_max_retries_from_config**
    - Установить smtp_max_retries=5
    - Проверить что система использует это значение

2. **test_custom_base_delay_from_config**
    - Установить smtp_retry_base_delay=10
    - Проверить что первая retry попытка ждет 10s

### Monitoring Tests

1. **test_retry_metrics_collected**
    - Отправить email с retry
    - Проверить что метрики собираются
    - Проверить retry_count, success после N попыток

2. **test_failed_email_metrics**
    - Email не доставляется после всех retry
    - Проверить что счетчик failed emails увеличивается

---

## Implementation Notes

- Создать класс `EmailRetryService` или `RetryManager` в `app/services/email_retry.py`
- Использовать exponential backoff для вычисления delay между попытками
- Логировать каждую попытку с номером, ошибкой и временем следующей попытки
- Использовать asyncio.sleep() для ожидания между попытками
- Можно использовать встроенный asyncio scheduler или интегрировать с Redis/Celery
- Сохранять историю попыток в БД или логе для аудита
- Интегрировать с EmailNotificationService
- Предусмотреть graceful shutdown retry задач при перезагрузке приложения
- Добавить параметры конфигурации в `app/core/config.py`: smtp_max_retries, smtp_retry_base_delay, smtp_retry_max_backoff
