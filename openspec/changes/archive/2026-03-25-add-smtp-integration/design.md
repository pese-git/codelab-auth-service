# Design: SMTP Email Integration для CodeLab Auth Service

**Версия:** 1.0.0  
**Дата:** 2026-03-23  
**Статус:** Design Phase  

---

## 📐 Architecture

### Общая архитектура интеграции

SMTP интеграция строится на **Layered Architecture** и встраивается в существующий **Service Layer** приложения. Система состоит из 4 взаимодополняющих компонентов:

```
┌─────────────────────────────────────────────┐
│         API Layer (register.py)             │
│    Точки вызова email operations            │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                Service Layer                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ EmailNotificationService                             │  │
│  │ - Управление типами уведомлений                     │  │
│  │ - Координирует отправку писем                       │  │
│  │ - Асинхронное выполнение через asyncio.create_task()│  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                          │
│  ┌──────────────┴──────────────────────────────────────┐  │
│  │                                                     │  │
│  ▼                                    ▼                ▼   │
│ ┌──────────────────────┐  ┌──────────────────┐  ┌────────────┐
│ │EmailTemplateEngine   │  │SMTPEmailSender   │  │EmailRetry  │
│ │- Jinja2 шаблоны      │  │- aiosmtplib      │  │Service     │
│ │- Рендеринг HTML/TEXT │  │- TLS/SSL         │  │- Exponential│
│ │- Управление context  │  │- Graceful errors │  │  backoff   │
│ │- XSS protection      │  │- Логирование     │  │- Retry loop│
│ └──────────────────────┘  └──────────────────┘  └────────────┘
│                                                             │
└─────────────────┬───────────────────────────────────────────┘
                  │
        ┌─────────┴──────────┬──────────────┐
        ▼                    ▼              ▼
     ┌────────┐          ┌──────────┐  ┌─────────┐
     │SQLite  │          │PostgreSQL│  │  Logs   │
     │(Dev)   │          │ (Prod)   │  │(Audit)  │
     └────────┘          └──────────┘  └─────────┘
```

### Компоненты системы

#### 1. EmailTemplateEngine (`app/services/email_templates.py`)

**Назначение:** Управление шаблонами писем и их рендерингом

**Ключевые классы:**

```python
class EmailTemplateEngine:
    """Управляет загрузкой и рендерингом email шаблонов"""
    
    def __init__(self, template_dir: str = "app/templates/emails"):
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True,  # Защита от XSS
            enable_async=True,  # Асинхронность
        )
    
    async def render_template(
        self, 
        template_name: str, 
        context: dict
    ) -> EmailMessage:
        """Рендерит шаблон и возвращает EmailMessage объект"""
        
    async def get_available_templates(self) -> List[str]:
        """Возвращает список доступных шаблонов"""
        
class EmailMessage:
    """Представление готового к отправке письма"""
    
    subject: str
    html_body: str
    text_body: str  # Автоматически создается из HTML
    to: str
    from_: str = settings.smtp_from_email
```

**Структура шаблонов:**

```
app/templates/emails/
├── base.html              # Базовый layout для всех писем
├── welcome/
│   ├── template.html      # HTML версия
│   ├── template.txt       # Текстовая версия (опционально)
│   └── subject.txt        # Тема письма
├── confirmation/
│   ├── template.html
│   ├── template.txt
│   └── subject.txt
├── password_reset/
│   ├── template.html
│   ├── template.txt
│   └── subject.txt
└── ...
```

**Переменные контекста по типам писем:**

- **welcome**: `username`, `email`, `activation_link`, `registration_date`
- **confirmation**: `username`, `confirmation_link`, `expires_at`
- **password_reset**: `username`, `reset_link`, `expires_at`

#### 2. SMTPEmailSender (`app/services/email_sender.py`)

**Назначение:** Фактическая отправка email через SMTP

**Ключевые методы:**

```python
class SMTPEmailSender:
    """Отправка email через aiosmtplib"""
    
    async def send_email(
        self,
        message: EmailMessage,
        timeout: int = 30
    ) -> bool:
        """
        Отправляет email через SMTP.
        
        Returns:
            True если успешно, False если ошибка
        """
        
    async def _create_smtp_connection(self) -> SMTP:
        """Создает SMTP соединение с TLS/SSL"""
        
    async def _handle_smtp_error(
        self, 
        error: Exception
    ) -> Tuple[bool, str]:
        """
        Классифицирует ошибку SMTP.
        
        Returns:
            (is_retryable, error_message)
        """
```

**Логика обработки TLS:**

```python
async with SMTP(
    hostname=settings.smtp_host,
    port=settings.smtp_port,
    timeout=timeout
) as smtp:
    if settings.smtp_use_tls:
        await smtp.starttls()  # STARTTLS для port 587
    
    if settings.smtp_username and settings.smtp_password:
        await smtp.login(
            settings.smtp_username, 
            settings.smtp_password
        )
    
    await smtp.sendmail(
        message.from_,
        message.to,
        message.as_string()
    )
```

**Обработка ошибок:**

- `SMTPAuthenticationError` → не повторять, логировать как CRITICAL
- `SMTPServerError` (4xx код) → повторить через retry service
- `SMTPServerError` (5xx код) → не повторять, логировать как ERROR
- `asyncio.TimeoutError` → повторить
- `ConnectionError` → повторить

#### 3. EmailNotificationService (`app/services/email_notifications.py`)

**Назначение:** Координирует отправку уведомлений при событиях

**Ключевые методы:**

```python
class EmailNotificationService:
    """Управляет отправкой email уведомлений"""
    
    async def send_welcome_email(
        self,
        user: User,
        background: bool = True
    ) -> bool:
        """Отправляет приветственное письмо"""
        
    async def send_confirmation_email(
        self,
        user: User,
        token: str,
        background: bool = True
    ) -> bool:
        """Отправляет письмо с подтверждением email"""
        
    async def send_password_reset_email(
        self,
        user: User,
        reset_token: str
    ) -> bool:
        """Отправляет письмо со сбросом пароля"""
        
    async def _send_async(
        self,
        message: EmailMessage,
        retry: bool = True
    ) -> bool:
        """Отправляет письмо асинхронно"""
```

**Интеграция с регистрацией:**

```python
# В app/api/v1/register.py после успешной регистрации:

async def register(...):
    user = await user_service.register_user(db, user_data)
    
    # Отправляем email в фоне (не блокируем API ответ)
    asyncio.create_task(
        email_notification_service.send_welcome_email(user, background=True)
    )
    
    if settings.require_email_confirmation:
        asyncio.create_task(
            email_notification_service.send_confirmation_email(
                user, 
                confirmation_token, 
                background=True
            )
        )
    
    return UserRegistrationResponse.model_validate(user)
```

**Конфигурационные параметры:**

```python
# В app/core/config.py добавляются:
send_welcome_email: bool = True
require_email_confirmation: bool = True  # уже есть
send_password_reset_email: bool = True
email_rate_limit_per_hour: int = 5  # макс писем на адрес в час
```

#### 4. EmailRetryService (`app/services/email_retry.py`)

**Назначение:** Управление повторными попытками отправки

**Ключевые методы:**

```python
class EmailRetryService:
    """Управляет retry логикой для отправки email"""
    
    async def send_with_retry(
        self,
        message: EmailMessage,
        max_retries: int = 3,
        base_delay: int = 5
    ) -> bool:
        """
        Отправляет email с автоматическим retry.
        
        Exponential backoff: delay = base_delay * (2 ^ attempt)
        """
        
    async def _calculate_backoff(
        self,
        attempt: int,
        base_delay: int = 5,
        max_backoff: int = 300
    ) -> float:
        """
        Вычисляет delay с exponential backoff и jitter.
        
        Formula:
        - backoff = base_delay * (2 ^ attempt)
        - capped at max_backoff (300s)
        - jitter = ±10%
        """
        import random
        
        backoff = min(
            base_delay * (2 ** attempt),
            max_backoff
        )
        jitter = backoff * random.uniform(-0.1, 0.1)
        return backoff + jitter
        
    async def _should_retry(
        self,
        error: Exception
    ) -> bool:
        """Определяет нужно ли повторять попытку"""
        
    async def _log_attempt(
        self,
        message: EmailMessage,
        attempt: int,
        error: Optional[Exception] = None
    ):
        """Логирует попытку отправки для аудита"""
```

**Стратегия retry:**

```
Попытка 1 (оригинальная):      t=0
Попытка 2 (retry):              t=5s + jitter (≈4.5-5.5s)
Попытка 3 (retry):              t=5s + 10s + jitter (≈13.5-16.5s)
Попытка 4 (retry):              t=5s + 10s + 20s + jitter (≈33.5-36.5s)
```

---

## 🔄 Data Flow

### Поток регистрации с отправкой email

```
1. Client POST /api/v1/register
   ├─ email: "user@example.com"
   ├─ username: "john_doe"
   └─ password: "secure_password"

2. API Layer (register.py)
   ├─ Валидация данных (Pydantic)
   └─ Передача в UserService

3. UserService.register_user()
   ├─ Проверка уникальности email/username
   ├─ Валидация пароля (min 8 chars)
   ├─ Хэширование пароля (bcrypt cost=12)
   ├─ Сохранение в БД
   └─ Возврат User объекта

4. Асинхронная отправка email
   ├─ asyncio.create_task(send_welcome_email(...))
   └─ asyncio.create_task(send_confirmation_email(...))
   
   [Основной thread продолжает работу, не ждет email]

5. BackgroundTask: send_welcome_email()
   ├─ EmailTemplateEngine.render_template("welcome", context)
   │  ├─ Загружает шаблон welcome/template.html
   │  ├─ Рендерит с переменными: {username, email, activation_link}
   │  ├─ Автоматически создает text версию (stripping HTML)
   │  └─ Возвращает EmailMessage
   │
   ├─ SMTPEmailSender.send_email(message)
   │  ├─ Создает SMTP соединение
   │  ├─ Выполняет starttls() (если smtp_use_tls=True)
   │  ├─ Логирует в (если есть credentials)
   │  ├─ Отправляет письмо
   │  └─ Возвращает True/False
   │
   └─ [Если ошибка] → EmailRetryService.send_with_retry()
      ├─ Классифицирует ошибку (retryable vs permanent)
      ├─ Вычисляет exponential backoff
      ├─ Логирует попытку
      ├─ await asyncio.sleep(delay)
      └─ Повторяет до max_retries или успеха

6. BackgroundTask: send_confirmation_email()
   ├─ EmailService.generate_confirmation_token()
   │  ├─ Генерирует secure random token (32 bytes)
   │  └─ Сохраняет в email_confirmation_tokens таблице
   │
   ├─ EmailTemplateEngine.render_template("confirmation", context)
   │  └─ context = {username, confirmation_link, expires_at}
   │
   └─ SMTPEmailSender.send_email() + retry logic
   
7. API ответ
   ├─ 201 Created
   ├─ UserRegistrationResponse
   │  ├─ id
   │  ├─ username
   │  ├─ email
   │  ├─ email_confirmed (false)
   │  └─ created_at
   └─ [Email отправляется в фоне, не влияет на HTTP response]

8. Аудит логирование
   ├─ AuditService.log_registration_success()
   ├─ AuditService.log_email_sent() [если успешно]
   └─ AuditService.log_email_failed() [если ошибка]
```

### Поток подтверждения email

```
1. User клика на ссылку из письма
   └─ GET /api/v1/confirm-email?token=<token>

2. API Layer
   ├─ Извлекает token из query параметров
   └─ Передает в EmailService

3. EmailService.verify_confirmation_token()
   ├─ Ищет token в email_confirmation_tokens
   ├─ Проверяет expires_at < now()
   ├─ Если валиден → User.email_confirmed = True
   ├─ Удаляет использованный token (one-time use)
   └─ Возвращает результат

4. API ответ
   ├─ 200 OK: "Email подтвержден"
   └─ 400 Bad Request: "Токен истек" или "Токен невалиден"
```

---

## 🛡️ Error Handling

### SMTP ошибки и стратегии обработки

| Ошибка | Тип | Retry? | Action |
|--------|-----|--------|--------|
| `SMTPAuthenticationError` | Конфигурация | ❌ | LOG CRITICAL, Не повторять |
| `SMTPServerError` (4xx) | Временная | ✅ | Retry с exponential backoff |
| `SMTPServerError` (5xx) | Постоянная | ❌ | LOG ERROR, Не повторять |
| `asyncio.TimeoutError` | Временная | ✅ | Retry с backoff |
| `ConnectionError` | Временная | ✅ | Retry с backoff |
| `OSError` | Временная | ✅ | Retry с backoff |

### Обработка ошибок в кодах

```python
async def send_email(message: EmailMessage) -> bool:
    """Отправка с обработкой ошибок"""
    try:
        async with SMTP(...) as smtp:
            await smtp.starttls()
            await smtp.login(...)
            await smtp.sendmail(...)
            
            logger.info(
                "Email sent successfully",
                extra={
                    "to": mask_email(message.to),
                    "template": message.template_name,
                }
            )
            return True
            
    except SMTPAuthenticationError as e:
        logger.critical(
            "SMTP Authentication failed - check credentials",
            extra={
                "error": str(e),
                "host": settings.smtp_host,
                # Не логируем password!
            }
        )
        return False
        
    except SMTPServerError as e:
        if e.smtp_code >= 500:
            # Постоянная ошибка
            logger.error(
                f"SMTP Server returned {e.smtp_code}",
                extra={"error": str(e)}
            )
            return False
        else:
            # Временная ошибка (4xx) - будет обработана retry service
            raise  # Re-raise для retry обработки
            
    except asyncio.TimeoutError:
        logger.warning(
            "SMTP connection timeout",
            extra={"timeout_seconds": 30}
        )
        raise  # Re-raise для retry
        
    except Exception as e:
        logger.error(
            f"Unexpected error during email send: {type(e).__name__}",
            exc_info=False,  # Не логируем stack trace в production
        )
        return False
```

### Graceful degradation

**Важно:** Ошибки отправки email НЕ должны прерывать основной процесс (регистрацию)

```python
# В register.py:
async def register(...):
    user = await user_service.register_user(db, user_data)
    
    # Отправляем email в фоне
    try:
        asyncio.create_task(
            email_notification_service.send_welcome_email(user)
        )
    except Exception as e:
        # Логируем, но не прерываем регистрацию
        logger.warning(
            f"Failed to schedule welcome email: {e}",
            extra={"user_id": user.id}
        )
    
    # API ответ возвращается независимо от статуса email
    return UserRegistrationResponse.model_validate(user)
```

---

## 🔐 Security

### 1. Защита от XSS в шаблонах

```python
# EmailTemplateEngine инициализируется с autoescape=True
jinja_env = Environment(
    loader=FileSystemLoader(template_dir),
    autoescape=True,  # Автоматически escapeит HTML спецсимволы
)
```

**Пример:** Если контекст содержит `<script>alert('xss')</script>`, он будет отображен как `&lt;script&gt;alert('xss')&lt;/script&gt;`

### 2. Безопасность SMTP credentials

```python
# ❌ Неправильно - логируем passwords
logger.info(f"Connecting to SMTP: {settings.smtp_host}:{settings.smtp_port} with user {settings.smtp_username} and password {settings.smtp_password}")

# ✅ Правильно - НЕ логируем credentials
logger.info(
    "SMTP connection established",
    extra={
        "host": settings.smtp_host,
        "port": settings.smtp_port,
        "auth": bool(settings.smtp_username),  # Only boolean
    }
)
```

### 3. TLS/SSL шифрование

**STARTTLS (port 587):**
```python
if settings.smtp_use_tls:
    await smtp.starttls()  # Upgrade to encrypted connection
```

**SSL (port 465):**
```python
# Для port 465 используется ssl.CERT_REQUIRED
async with SMTP_SSL(
    hostname=settings.smtp_host,
    port=465,
    ssl_context=ssl.create_default_context()
) as smtp:
    await smtp.login(...)
```

### 4. Защита token-ов подтверждения

- Генерируются через `secrets.token_urlsafe(32)` (256 бит энтропии)
- Хранятся в БД только один раз (one-time use)
- Автоматически удаляются после использования
- Имеют TTL (обычно 24 часа)
- Не передаются в логах

```python
token = secrets.token_urlsafe(32)  # 43 символа в URL-safe формате

# Сохраняется как:
confirmation_token = EmailConfirmationToken(
    user_id=user.id,
    token=token,
    expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
)
```

### 5. Масккирование email в логах

```python
def mask_email(email: str) -> str:
    """Маскирует email для логов"""
    local, domain = email.split('@')
    return f"{local[0]}***{local[-1]}@{domain}"

# Результат: "u***r@example.com"
```

---

## ⚡ Performance

### 1. Асинхронность

Все операции отправки email выполняются асинхронно, не блокируя основной thread:

```python
# В register.py - не ждем завершения email отправки
asyncio.create_task(
    email_notification_service.send_welcome_email(user)
)

# Ответ API возвращается сразу (201 Created)
return UserRegistrationResponse.model_validate(user)
```

**Измерение:** Регистрация с email отправкой должна завершиться за <100ms (без учета email доставки)

### 2. Кэширование шаблонов

```python
class EmailTemplateEngine:
    def __init__(self, template_dir: str):
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
        self._template_cache = {}  # In-memory cache
    
    async def render_template(self, template_name: str, context: dict):
        # Шаблоны компилируются один раз и кэшируются Jinja2
        if template_name not in self._template_cache:
            self._template_cache[template_name] = \
                self.jinja_env.get_template(f"{template_name}/template.html")
        
        return self._template_cache[template_name].render(context)
```

### 3. Объединение SMTP соединений

Для высоконагруженных систем можно использовать connection pooling:

```python
class SMTPEmailSender:
    def __init__(self):
        # Опциональная реализация connection pool
        self.connection_pool = asyncio.Queue(maxsize=10)
        
    async def _get_connection(self) -> SMTP:
        """Получить соединение из пула или создать новое"""
        try:
            return self.connection_pool.get_nowait()
        except asyncio.QueueEmpty:
            return await self._create_smtp_connection()
```

### 4. Batch отправка (опционально)

Для отправки большого количества email (например, newsletter), можно оптимизировать:

```python
async def send_batch_emails(messages: List[EmailMessage]) -> Dict[str, bool]:
    """Отправляет множество писем в одном SMTP соединении"""
    results = {}
    
    async with SMTP(...) as smtp:
        for message in messages:
            try:
                await smtp.sendmail(message.from_, message.to, ...)
                results[message.to] = True
            except Exception as e:
                results[message.to] = False
    
    return results
```

---

## 🧪 Testing Strategy

### Unit Tests

#### 1. EmailTemplateEngine tests

```python
@pytest.mark.asyncio
async def test_render_welcome_template():
    """Проверка рендеринга приветственного шаблона"""
    engine = EmailTemplateEngine()
    context = {
        "username": "john_doe",
        "email": "john@example.com",
        "activation_link": "https://auth.local/activate?token=abc123"
    }
    
    message = await engine.render_template("welcome", context)
    
    assert message.subject is not None
    assert "john_doe" in message.html_body
    assert "john@example.com" in message.html_body
    assert message.text_body is not None  # Auto-generated

@pytest.mark.asyncio
async def test_xss_prevention():
    """Проверка защиты от XSS инъекций"""
    engine = EmailTemplateEngine()
    context = {
        "username": "<script>alert('xss')</script>",
        "email": "user@example.com",
        "activation_link": "https://auth.local/activate"
    }
    
    message = await engine.render_template("welcome", context)
    
    assert "<script>" not in message.html_body
    assert "&lt;script&gt;" in message.html_body  # Properly escaped
```

#### 2. SMTPEmailSender tests

```python
@pytest.mark.asyncio
async def test_send_email_success(mock_aiosmtplib):
    """Проверка успешной отправки email"""
    mock_aiosmtplib.return_value.__aenter__.return_value.sendmail = \
        AsyncMock(return_value=None)
    
    sender = SMTPEmailSender()
    message = EmailMessage(
        to="user@example.com",
        subject="Welcome",
        html_body="<p>Welcome</p>",
        text_body="Welcome"
    )
    
    result = await sender.send_email(message)
    
    assert result is True
    mock_aiosmtplib.return_value.__aenter__.return_value.starttls.assert_called_once()

@pytest.mark.asyncio
async def test_smtp_auth_error_no_retry(mock_aiosmtplib):
    """Проверка что SMTPAuthenticationError не повторяется"""
    mock_aiosmtplib.return_value.__aenter__.return_value.login = \
        AsyncMock(side_effect=SMTPAuthenticationError(535, "Auth failed"))
    
    sender = SMTPEmailSender()
    message = EmailMessage(to="user@example.com", subject="", html_body="", text_body="")
    
    result = await sender.send_email(message)
    
    assert result is False
    # Проверяем что retry service не будет вызван
    mock_aiosmtplib.return_value.__aenter__.return_value.sendmail.assert_not_called()
```

#### 3. EmailRetryService tests

```python
@pytest.mark.asyncio
async def test_exponential_backoff_calculation():
    """Проверка расчета exponential backoff"""
    retry_service = EmailRetryService()
    
    delay_1 = await retry_service._calculate_backoff(attempt=0, base_delay=5)
    delay_2 = await retry_service._calculate_backoff(attempt=1, base_delay=5)
    delay_3 = await retry_service._calculate_backoff(attempt=2, base_delay=5)
    
    assert 4.5 <= delay_1 <= 5.5  # 5s ± 10%
    assert 9 <= delay_2 <= 11      # 10s ± 10%
    assert 18 <= delay_3 <= 22     # 20s ± 10%

@pytest.mark.asyncio
async def test_retry_with_timeout(mock_sender):
    """Проверка retry при timeout"""
    mock_sender.send_email = AsyncMock(
        side_effect=[
            asyncio.TimeoutError(),  # First attempt
            asyncio.TimeoutError(),  # Second attempt
            True                      # Third attempt succeeds
        ]
    )
    
    retry_service = EmailRetryService()
    result = await retry_service.send_with_retry(
        message=mock_message,
        max_retries=3
    )
    
    assert result is True
    assert mock_sender.send_email.call_count == 3
```

#### 4. EmailNotificationService tests

```python
@pytest.mark.asyncio
async def test_send_welcome_email_background():
    """Проверка отправки welcome email в фоне"""
    notification_service = EmailNotificationService()
    user = User(
        id="123",
        username="john",
        email="john@example.com"
    )
    
    result = await notification_service.send_welcome_email(
        user,
        background=True
    )
    
    assert result is True or result is None  # Background task не блокирует

@pytest.mark.asyncio
async def test_registration_succeeds_even_if_email_fails(
    mock_email_service,
    mock_user_service
):
    """Проверка что ошибка email не прерывает регистрацию"""
    mock_email_service.send_welcome_email = AsyncMock(side_effect=Exception("SMTP failed"))
    mock_user_service.register_user = AsyncMock(return_value=user)
    
    response = await register(
        request=mock_request,
        user_data=UserRegister(...),
        db=mock_db
    )
    
    assert response.status_code == 201  # Регистрация успешна
    # Email ошибка логируется, но не влияет на результат
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_end_to_end_registration_with_email():
    """End-to-end тест регистрации с отправкой email"""
    # Используем fake-smtp-server или MailHog
    
    # 1. Регистрируем пользователя
    response = await client.post(
        "/api/v1/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "SecurePass123"
        }
    )
    
    assert response.status_code == 201
    
    # 2. Проверяем что email получен на mock SMTP сервере
    await asyncio.sleep(1)  # Ждем асинхронной отправки
    
    emails = await mock_smtp_server.get_emails()
    assert len(emails) == 2  # Welcome + Confirmation
    
    # 3. Извлекаем token из письма
    confirmation_email = emails[1]
    token = extract_token_from_email(confirmation_email.body)
    
    # 4. Подтверждаем email
    confirm_response = await client.get(
        f"/api/v1/confirm-email?token={token}"
    )
    
    assert confirm_response.status_code == 200
    
    # 5. Проверяем что user.email_confirmed установлен
    user = await db.get(User, user_id)
    assert user.email_confirmed is True
```

### Security Tests

```python
@pytest.mark.asyncio
async def test_no_credentials_in_logs(caplog):
    """Проверка что credentials не логируются"""
    sender = SMTPEmailSender()
    
    try:
        await sender.send_email(message)
    except:
        pass
    
    log_contents = caplog.text
    assert settings.smtp_password not in log_contents
    assert "***" not in log_contents or "password" not in log_contents.lower()

@pytest.mark.asyncio
async def test_tls_enabled_by_default(mock_aiosmtplib):
    """Проверка что TLS включен по умолчанию"""
    sender = SMTPEmailSender()
    await sender.send_email(message)
    
    # Проверяем что starttls() был вызван
    mock_aiosmtplib.return_value.__aenter__.return_value.starttls.assert_called_once()
```

---

## 📋 Implementation Checklist

Перед началом разработки убедиться что:

- [ ] Проверены все требования из 4 specs
- [ ] Структура шаблонов создана (`app/templates/emails/`)
- [ ] Зависимости добавлены в `pyproject.toml` (`aiosmtplib`, `jinja2`)
- [ ] Конфигурация SMTP параметров обновлена в `app/core/config.py`
- [ ] Созданы все service классы согласно дизайну
- [ ] Интегрирована отправка email в `app/api/v1/register.py`
- [ ] Unit и integration тесты написаны и проходят
- [ ] Логирование настроено без утечки credentials
- [ ] TLS/SSL правильно сконфигурирован

---

## 📖 References

- **aiosmtplib**: https://github.com/cole/aiosmtplib
- **Jinja2**: https://jinja.palletsprojects.com/
- **asyncio documentation**: https://docs.python.org/3/library/asyncio.html
- **SMTP RFC 5321**: https://tools.ietf.org/html/rfc5321
- **OWASP XSS Prevention**: https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html

---

**Статус:** Ready for Implementation  
**Следующий артефакт:** tasks.md (Break down into implementation tasks)
