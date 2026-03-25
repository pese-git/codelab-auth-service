# Integration Tests Guide

## Overview

Phase 10 создает полные integration тесты для SMTP функциональности. Тесты проверяют весь цикл работы email-сервиса с реальным SMTP сервером (MailHog).

## Prerequisites

### MailHog
Integration тесты требуют запущенного MailHog сервера:
- SMTP: `localhost:1025`
- Web UI: `http://localhost:8025`
- HTTP API: `http://localhost:8025/api/v1`

## Running Integration Tests

### Option 1: With Docker Compose (Recommended)

```bash
# Start all services including MailHog
docker-compose up -d

# Run integration tests
pytest tests/integration/ -v -m integration

# Run with coverage
pytest tests/integration/ -v -m integration --cov=app --cov-report=html

# Stop services
docker-compose down
```

### Option 2: With Local MailHog Instance

```bash
# Start MailHog locally
# macOS with Homebrew:
brew install mailhog
brew services start mailhog

# Or run Docker container:
docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog

# Run integration tests
pytest tests/integration/ -v -m integration
```

### Option 3: Run Only Unit Tests (Skip Integration)

```bash
# Run all tests except integration
pytest tests/ -v -m "not integration"

# Or run specific unit tests
pytest tests/test_email_sender.py -v
pytest tests/test_email_templates.py -v
pytest tests/test_email_retry.py -v
```

## Test Structure

### Test Classes

1. **TestSMTPFullCycle** - Полный цикл SMTP отправки
   - `test_full_smtp_cycle_welcome_email` - Welcome email
   - `test_full_smtp_cycle_confirmation_email` - Confirmation email
   - `test_full_smtp_cycle_password_reset_email` - Password reset email

2. **TestRetryLogic** - Retry логика при временных ошибках
   - `test_retry_on_temporary_smtp_error` - Retry при 4xx ошибках
   - `test_retry_with_exponential_backoff` - Exponential backoff timing
   - `test_retry_max_attempts_exceeded` - Max retries handling

3. **TestPermanentErrors** - Обработка permanent ошибок
   - `test_no_retry_on_permanent_smtp_error` - Нет retry для 5xx
   - `test_permanent_error_logging` - Логирование ошибок

4. **TestMultipleEmails** - Отправка нескольких писем
   - `test_multiple_users_receive_correct_emails` - Разные получатели
   - `test_concurrent_email_sending` - Concurrent отправка

5. **TestEmailContent** - Проверка содержимого писем
   - `test_email_headers_and_subject` - Headers и subject
   - `test_email_body_content` - Body content

6. **TestMailHogIntegration** - MailHog API тесты
   - `test_mailhog_api_connectivity` - Доступность API
   - `test_mailhog_cleanup` - Cleanup функциональность

## Fixtures

### `mailhog_client`
MailHog HTTP API client для проверки доставленных писем.

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_example(mailhog_client):
    # Get all messages
    messages = await mailhog_client.get_all_messages()
    
    # Get messages for recipient
    messages = await mailhog_client.get_messages_for_recipient("user@example.com")
    
    # Wait for message with timeout
    msg = await mailhog_client.verify_message_received(
        "user@example.com",
        subject="Test Email",
        timeout=5
    )
    
    # Get message count
    count = await mailhog_client.get_message_count()
```

### `cleanup_mailhog`
Очищает MailHog перед и после каждого теста.

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_example(cleanup_mailhog, mailhog_client):
    # MailHog будет очищен перед тестом
    # ... test code ...
    # MailHog будет очищен после теста
```

### `integration_test_config`
Configuration для integration тестов (session-scoped).

## Pytest Markers

### Integration marker
```bash
# Run only integration tests
pytest -m integration

# Run without integration tests
pytest -m "not integration"
```

### Async marker
```bash
# Автоматически применяется благодаря pytest-asyncio
@pytest.mark.asyncio
async def test_something():
    pass
```

## Environment Variables

```bash
# MailHog configuration
export MAILHOG_HOST=localhost
export MAILHOG_SMTP_PORT=1025
export MAILHOG_HTTP_PORT=8025

# SMTP sender configuration
export AUTH_SERVICE__SMTP_HOST=mailhog
export AUTH_SERVICE__SMTP_PORT=1025
export AUTH_SERVICE__SMTP_USE_TLS=false
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    
    services:
      mailhog:
        image: mailhog/mailhog
        ports:
          - 1025:1025
          - 8025:8025

    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.12
      
      - name: Install dependencies
        run: |
          pip install -e .
          pip install -e ".[dev]"
      
      - name: Run integration tests
        run: |
          pytest tests/integration/ -v -m integration --cov=app
```

### Docker Compose for CI

```bash
docker-compose -f docker-compose.yml up -d
pytest tests/integration/ -v -m integration
docker-compose down
```

## Troubleshooting

### MailHog Not Available
Если тесты пропускаются с сообщением "MailHog is not available":

```bash
# Проверьте что MailHog запущен
curl http://localhost:8025/api/v1/messages

# Если 404 или connection refused, запустите MailHog:
docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog
```

### Email Not Received
Если тесты падают на проверке доставки:

1. Проверьте что SMTP сервер доступен:
```bash
telnet localhost 1025
```

2. Увеличьте timeout в тесте:
```python
msg = await mailhog_client.verify_message_received(
    recipient,
    subject="Test",
    timeout=10  # увеличьте timeout
)
```

3. Проверьте логи MailHog:
```bash
docker logs mailhog
```

### Port Already in Use
Если порты 1025 или 8025 уже используются:

```bash
# Найдите процесс
lsof -i :1025
lsof -i :8025

# Или используйте другие порты
docker run -d -p 1026:1025 -p 8026:8025 mailhog/mailhog
export MAILHOG_SMTP_PORT=1026
export MAILHOG_HTTP_PORT=8026
```

## Performance Notes

- **Cleanup between tests**: Каждый тест очищает MailHog перед и после
- **Async operations**: Все тесты используют async/await для параллельной обработки
- **Timeouts**: Тесты используют 5-секундные таймауты для доставки

## Best Practices

1. **Always use cleanup_mailhog fixture** для isolation тестов
2. **Use specific subjects** для easier message identification
3. **Validate content** в addition to headers
4. **Test error cases** with proper mocking
5. **Keep tests independent** от друг друга

## Adding New Integration Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_new_feature(cleanup_mailhog, mailhog_client):
    """Test description"""
    from app.services.email_sender import SMTPEmailSender
    from app.services.email_templates import EmailMessage
    
    # Setup
    sender = SMTPEmailSender()
    recipient = "test@example.com"
    
    # Execute
    message = EmailMessage(
        subject="Test",
        html_body="<p>Test</p>",
        text_body="Test",
        to=recipient,
        from_="noreply@codelab.local",
        template_name="test"
    )
    result = await sender.send_email(message)
    
    # Verify
    assert result is True
    
    await asyncio.sleep(0.5)
    received = await mailhog_client.verify_message_received(
        recipient,
        subject="Test"
    )
    assert received is not None
```

## References

- [MailHog Documentation](https://github.com/mailhog/MailHog)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [aiosmtplib](https://github.com/cole/aiosmtplib)
- [httpx](https://www.python-httpx.org/)
