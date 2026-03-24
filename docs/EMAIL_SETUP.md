# Email Setup Guide для CodeLab Auth Service

## Содержание

- [Обзор](#обзор)
- [Конфигурация SMTP](#конфигурация-smtp)
- [Поддерживаемые SMTP провайдеры](#поддерживаемые-smtp-провайдеры)
- [Компоненты системы email](#компоненты-системы-email)
- [API endpoints](#api-endpoints)
- [Troubleshooting](#troubleshooting)

## Обзор

CodeLab Auth Service включает полнофункциональную систему отправки email с поддержкой:
- 📧 **Асинхронная отправка** - не блокирует основной процесс
- 🔄 **Automatic Retry** - exponential backoff для надежности
- 🎨 **HTML шаблоны** - Jinja2 для динамического контента
- 🔒 **Безопасность** - TLS/SSL шифрование, маскирование данных в логах
- ⚙️ **Конфигурируемость** - полный контроль через переменные окружения

## Конфигурация SMTP

### Переменные окружения

```bash
# Основные параметры SMTP
AUTH_SERVICE__SMTP_HOST=smtp.example.com        # SMTP сервер (обязательно)
AUTH_SERVICE__SMTP_PORT=587                     # SMTP порт (обязательно)
AUTH_SERVICE__SMTP_USERNAME=user@example.com    # Имя пользователя (опционально)
AUTH_SERVICE__SMTP_PASSWORD=password            # Пароль (опционально, чувствительный)
AUTH_SERVICE__SMTP_FROM_EMAIL=noreply@example.com  # Адрес отправителя (обязательно)

# Дополнительные параметры
AUTH_SERVICE__SMTP_USE_TLS=true                 # Использовать TLS (default: true)
AUTH_SERVICE__SMTP_TIMEOUT=30                   # Таймаут в секундах (default: 30)
AUTH_SERVICE__SMTP_MAX_RETRIES=3                # Максимум попыток (default: 3)

# Управление типами уведомлений
AUTH_SERVICE__SEND_WELCOME_EMAIL=true           # Отправлять приветственное письмо
AUTH_SERVICE__REQUIRE_EMAIL_CONFIRMATION=true   # Требовать подтверждение email
AUTH_SERVICE__SEND_PASSWORD_RESET_EMAIL=true    # Отправлять письма сброса пароля
```

### Пример .env файла

```bash
# Development (MailHog)
AUTH_SERVICE__SMTP_HOST=mailhog
AUTH_SERVICE__SMTP_PORT=1025
AUTH_SERVICE__SMTP_USERNAME=
AUTH_SERVICE__SMTP_PASSWORD=
AUTH_SERVICE__SMTP_FROM_EMAIL=noreply@codelab.local
AUTH_SERVICE__SMTP_USE_TLS=false

# Production (SendGrid)
AUTH_SERVICE__SMTP_HOST=smtp.sendgrid.net
AUTH_SERVICE__SMTP_PORT=587
AUTH_SERVICE__SMTP_USERNAME=apikey
AUTH_SERVICE__SMTP_PASSWORD=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AUTH_SERVICE__SMTP_FROM_EMAIL=noreply@yourdomain.com
AUTH_SERVICE__SMTP_USE_TLS=true
```

## Поддерживаемые SMTP провайдеры

### MailHog (Development)

**Рекомендуется для локальной разработки**

```bash
AUTH_SERVICE__SMTP_HOST=mailhog
AUTH_SERVICE__SMTP_PORT=1025
AUTH_SERVICE__SMTP_USE_TLS=false

# Web UI: http://localhost:8025
# SMTP: localhost:1025
```

**Docker Compose пример:**
```yaml
services:
  mailhog:
    image: mailhog/mailhog:latest
    ports:
      - "1025:1025"   # SMTP
      - "8025:8025"   # Web UI
```

### SendGrid

```bash
AUTH_SERVICE__SMTP_HOST=smtp.sendgrid.net
AUTH_SERVICE__SMTP_PORT=587
AUTH_SERVICE__SMTP_USERNAME=apikey
AUTH_SERVICE__SMTP_PASSWORD=SG.your_api_key_here
AUTH_SERVICE__SMTP_FROM_EMAIL=noreply@yourdomain.com
AUTH_SERVICE__SMTP_USE_TLS=true
```

**Получение API ключа:**
1. Создайте аккаунт на https://sendgrid.com
2. Перейдите в Settings → API Keys
3. Создайте новый API ключ с правом "Mail Send"
4. Используйте ключ в переменной окружения

### AWS SES

```bash
AUTH_SERVICE__SMTP_HOST=email-smtp.us-east-1.amazonaws.com
AUTH_SERVICE__SMTP_PORT=587
AUTH_SERVICE__SMTP_USERNAME=your_smtp_username
AUTH_SERVICE__SMTP_PASSWORD=your_smtp_password
AUTH_SERVICE__SMTP_FROM_EMAIL=verified-email@yourdomain.com
AUTH_SERVICE__SMTP_USE_TLS=true
```

**Требования:**
- Email адрес должен быть верифицирован в SES
- Получите SMTP учетные данные из консоли AWS

### Mailgun

```bash
AUTH_SERVICE__SMTP_HOST=smtp.mailgun.org
AUTH_SERVICE__SMTP_PORT=587
AUTH_SERVICE__SMTP_USERNAME=postmaster@yourdomain.mailgun.org
AUTH_SERVICE__SMTP_PASSWORD=your_password
AUTH_SERVICE__SMTP_FROM_EMAIL=noreply@yourdomain.com
AUTH_SERVICE__SMTP_USE_TLS=true
```

## Компоненты системы email

### 1. Email Templates (`app/templates/emails/`)

Система использует Jinja2 шаблоны для генерации email:

- **welcome/** - Приветственное письмо при регистрации
  - Переменные: `username`, `email`, `activation_link`, `registration_date`
  
- **confirmation/** - Подтверждение email адреса
  - Переменные: `username`, `confirmation_link`, `expires_at`
  
- **password_reset/** - Сброс пароля
  - Переменные: `username`, `reset_link`, `expires_at`

Каждый шаблон состоит из:
- `template.html` - HTML версия письма
- `subject.txt` - Тема письма
- `base.html` - Базовый layout (наследуется всеми)

### 2. Services

**EmailTemplateEngine** (`app/services/email_templates.py`)
- Рендеринг Jinja2 шаблонов
- Автоматическая генерация текстовой версии из HTML
- Защита от XSS (autoescape=True)

**SMTPEmailSender** (`app/services/email_sender.py`)
- Асинхронная отправка через SMTP
- Поддержка TLS/STARTTLS
- Graceful error handling
- Логирование без раскрытия credentials

**EmailRetryService** (`app/services/email_retry.py`)
- Exponential backoff retry логика
- Определение retryable vs permanent ошибок
- Jitter для避免 thundering herd
- Логирование всех попыток

**EmailNotificationService** (`app/services/email_notifications.py`)
- Высокоуровневый API для отправки уведомлений
- Поддержка background tasks
- Конфигурационные флаги для управления уведомлениями

**EmailService** (`app/services/email_service.py`)
- Управление confirmation токенами
- Верификация email адреса
- Интеграция с `EmailNotificationService`

## API Endpoints

### POST /api/v1/register

Регистрация нового пользователя с автоматической отправкой email

**Request:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePassword123!"
}
```

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "email": "john@example.com",
  "email_confirmed": false,
  "created_at": "2026-03-24T20:10:10.525Z"
}
```

**Email автоматически отправляются:**
- ✉️ Welcome email (если `SEND_WELCOME_EMAIL=true`)
- ✉️ Confirmation email (если `REQUIRE_EMAIL_CONFIRMATION=true`)

### GET /api/v1/confirm-email

Подтверждение email адреса по токену из письма

**Query Parameters:**
- `token` - Confirmation token из письма

**Response (200 OK):**
```json
{
  "message": "Email confirmed successfully",
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Errors:**
- **400 Bad Request** - Токен неверный или истек
- **500 Internal Server Error** - Ошибка сервера

## Troubleshooting

### SMTP Authentication Failed

**Симптом:** `SMTPAuthenticationError: SMTP authentication failed`

**Решение:**
1. Проверьте правильность `SMTP_USERNAME` и `SMTP_PASSWORD`
2. Убедитесь что учетные данные кодированы правильно (особенно специальные символы)
3. Проверьте что пользователь имеет права на отправку email

### Connection Refused

**Симптом:** `ConnectionError: SMTP server refused connection`

**Решение:**
1. Проверьте что SMTP сервер доступен: `telnet smtp.example.com 587`
2. Проверьте правильность `SMTP_HOST` и `SMTP_PORT`
3. Проверьте firewall правила
4. Убедитесь что SMTP сервис запущен

### TLS/SSL Errors

**Симптом:** `SSLError: CERTIFICATE_VERIFY_FAILED`

**Решение:**
1. Убедитесь что `SMTP_USE_TLS=true` установлен правильно
2. Для порта 465 используйте SSL (может потребоваться `SMTP_USE_TLS=true`)
3. Для порта 587 используйте STARTTLS

### Email не отправляется

**Симптом:** Регистрация успешна но email не приходит

**Решение:**
1. Проверьте что `SEND_WELCOME_EMAIL=true` в конфигурации
2. Проверьте SMTP сервер логи
3. Проверьте папку Spam/Junk
4. Посмотрите логи приложения: `grep "email" logs/app.log`

### Timeout ошибки

**Симптом:** `asyncio.TimeoutError: SMTP connection timeout`

**Решение:**
1. Увеличьте `SMTP_TIMEOUT` (default: 30 сек)
2. Проверьте сетевое соединение
3. Убедитесь что SMTP сервер не перегружен

## Мониторинг

### Логирование

Система логирует все email операции на уровне INFO/WARNING/ERROR:

```
2026-03-24 20:10:10 - auth-service - INFO - Email sent successfully to u***@example.com (template: welcome)
2026-03-24 20:10:15 - auth-service - WARNING - SMTP temporary error (450): Try again later
2026-03-24 20:10:20 - auth-service - INFO - Retry attempt 1/3 for u***@example.com in 2.15s
```

### Metrics

- Количество успешно отправленных email
- Процент успешных доставок
- Среднее время доставки
- Ошибки по типам

## Best Practices

1. **Development:** Используйте MailHog для локальной разработки
2. **Testing:** Используйте mock SMTP для unit тестов
3. **Production:** Используйте надежный SMTP провайдер (SendGrid, AWS SES)
4. **Security:** Никогда не коммитьте пароли в git, используйте переменные окружения
5. **Monitoring:** Настройте alerting на критические ошибки
6. **Backup:** Сохраняйте backup шаблонов email отдельно от кода
