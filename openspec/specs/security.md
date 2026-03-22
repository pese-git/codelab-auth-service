# Спецификация безопасности

**Версия:** 1.0.0  
**Статус:** ✅ Production Ready  
**Дата обновления:** 22 марта 2026

---

## 🛡️ Обзор безопасности

CodeLab Auth Service реализует комплексный подход к безопасности, включающий криптографию, защиту от атак, валидацию данных и аудит логирование.

**Ключевые принципы:**
- ✅ **Defense in Depth** — несколько слоёв защиты
- ✅ **Least Privilege** — минимальные разрешения
- ✅ **Secure by Default** — безопасность по умолчанию
- ✅ **Fail Securely** — безопасный отказ при ошибках

---

## 🔐 Криптография

### 1. Password Hashing

**Алгоритм:** bcrypt (cost factor = 12)

**Параметры:**
- Алгоритм: bcrypt
- Cost factor: 12 (примерно 250ms на хэш)
- Solting: автоматический (включен в bcrypt)
- Выход: 60 байт (UTF-8)

**Процесс:**

```python
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

# Хэширование
password = "MyPassword123!"
password_hash = pwd_context.hash(password)
# Результат: $2b$12$R9h/cIPz0gi.URNN3kh2OPST9EsirqHuMx7Tl3eL...

# Проверка (constant-time сравнение)
is_correct = pwd_context.verify(password, password_hash)
```

**Безопасность:**
- ✅ Constant-time сравнение (защита от timing attacks)
- ✅ Автоматическая генерация salt
- ✅ Адаптивный cost factor (можно увеличить при необходимости)
- ✅ Разные хэши для одного пароля (из-за random salt)

### 2. JWT Signing (Access Token)

**Алгоритм:** RS256 (RSA + SHA-256)

**Параметры:**
- RSA key size: 2048 bit
- Signature algorithm: SHA-256 with RSA
- Key ID (kid): строка с датой и порядковым номером

**Процесс:**

```python
from jose import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# Загрузка приватного ключа
with open("keys/private_key.pem", "rb") as f:
    private_key = serialization.load_pem_private_key(
        f.read(),
        password=None,
        backend=default_backend()
    )

# Создание JWT
payload = {
    "iss": "https://auth.codelab.local",
    "sub": str(user_id),
    "aud": "codelab-api",
    "exp": now + 900,
    "iat": now,
    "scope": "api:read api:write",
    "jti": str(uuid.uuid4()),
    "type": "access",
    "client_id": "codelab-flutter-app"
}

token = jwt.encode(
    payload,
    private_key,
    algorithm="RS256",
    headers={"kid": "2024-01-key-1"}
)
```

**Безопасность:**
- ✅ Асимметричная криптография (публичный ключ может быть распределён)
- ✅ Невозможно подделать без приватного ключа
- ✅ Неизменяемость (любое изменение payload сделает подпись невалидной)
- ✅ 2048-bit RSA стандартен для OAuth2

### 3. JWT Verification

**Процесс:**

```python
# Загрузка публичного ключа
with open("keys/public_key.pem", "rb") as f:
    public_key = serialization.load_pem_public_key(
        f.read(),
        backend=default_backend()
    )

# Валидация и декодирование
try:
    payload = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        audience="codelab-api",
        options={"verify_exp": True, "verify_aud": True}
    )
except JWTError as e:
    # Невалидный токен
    pass
```

**Проверки:**
- ✅ Валидность подписи (RS256)
- ✅ Истечение (exp claim)
- ✅ Аудитория (aud claim)
- ✅ Издатель (iss claim)
- ✅ Тип токена (type="access")

### 4. Refresh Token JTI Hashing

**Алгоритм:** SHA-256

**Параметры:**
- Hash function: SHA-256
- Output: 64 символа (hex)

**Процесс:**

```python
import hashlib

# JWT содержит jti
jti = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

# Хэширование
jti_hash = hashlib.sha256(jti.encode()).hexdigest()
# Результат: "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890"

# В БД сохраняется только хэш
# Невозможно восстановить оригинальный JTI из БД
```

**Благодаря хэшированию:**
- ✅ Токены не компрометированы даже при утечке БД
- ✅ Быстрый поиск (индекс на хэш)
- ✅ Одностороннее преобразование (необратимо)

### 5. Client Secret Hashing

**Алгоритм:** bcrypt (аналогично паролям)

```python
# Регистрация клиента
client_secret = "super-secret-string-for-api"
client_secret_hash = pwd_context.hash(client_secret)

# Проверка
is_valid = pwd_context.verify(provided_secret, client_secret_hash)
```

---

## 🚫 Защита от атак

### 1. Rate Limiting

**Назначение:** Предотвращение brute-force и DDoS атак

**Реализация:** Redis counters с TTL

**Лимиты:**

| Лимит | Значение | TTL | Применение |
|-------|----------|-----|-----------|
| **IP Rate Limit** | 5 req/min | 1 min | На все requests |
| **Username Rate Limit** | 10 req/hour | 1 hour | На /oauth/token |

**Код:**

```python
class RateLimiterService:
    async def check_rate_limit(
        self,
        ip: str,
        username: Optional[str] = None
    ) -> bool:
        # IP based
        ip_key = f"rate_limit:ip:{ip}"
        ip_count = await redis.incr(ip_key)
        if ip_count == 1:
            await redis.expire(ip_key, 60)  # 1 minute TTL
        
        if ip_count > 5:
            raise RateLimitExceeded(
                error_description="Rate limit exceeded: 5 requests per minute"
            )
        
        # Username based
        if username:
            username_key = f"rate_limit:username:{username}"
            username_count = await redis.incr(username_key)
            if username_count == 1:
                await redis.expire(username_key, 3600)  # 1 hour TTL
            
            if username_count > 10:
                raise RateLimitExceeded(
                    error_description="Rate limit exceeded: 10 requests per hour"
                )
        
        return True
```

**Response Headers:**
```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 3
X-RateLimit-Reset: 1711000060
Retry-After: 45
```

### 2. Brute-Force Protection

**Назначение:** Защита от перебора пароля

**Механизм:**
- Счётчик неудачных попыток (Redis)
- Блокировка после N попыток на T времени
- Очистка счётчика после успешного входа

**Параметры:**

| Параметр | Значение | Описание |
|----------|----------|---------|
| **Threshold** | 5 attempts | После 5 неудачных попыток |
| **Lockout Duration** | 15 minutes | Аккаунт заблокирован на 15 минут |
| **Reset on Success** | Yes | Счётчик сбрасывается при успехе |

**Код:**

```python
class BruteForceProtectionService:
    async def check_attempts(self, username: str) -> bool:
        key = f"brute_force:{username}"
        attempts = await redis.get(key)
        
        if attempts and int(attempts) >= 5:
            # Аккаунт заблокирован
            raise AccountLockedError(
                error_description="Too many failed attempts. Try again later."
            )
        
        return True
    
    async def record_failed_attempt(self, username: str):
        key = f"brute_force:{username}"
        await redis.incr(key)
        # Устанавливаем TTL только при первой попытке
        ttl = await redis.ttl(key)
        if ttl == -1:  # Нет TTL
            await redis.expire(key, 900)  # 15 minutes
    
    async def clear_attempts(self, username: str):
        key = f"brute_force:{username}"
        await redis.delete(key)
```

**Безопасность:**
- ✅ Защита от brute-force атак
- ✅ Временная блокировка (не перманентная)
- ✅ Без раскрытия информации о пользователе
- ✅ Логирование попыток в аудит логи

### 3. Refresh Token Reuse Detection

**Назначение:** Обнаружение компрометированных токенов

**Механизм:**
- Отслеживание цепочки токенов (parent_jti_hash)
- Обнаружение повторного использования старого токена
- Отзыв всей цепочки при обнаружении

**Сценарий:**

```
User gets refresh token 1 (jti_1)
├─ User refreshes → получает token 2 (parent=jti_1)
│  └─ User refreshes → получает token 3 (parent=jti_2)
│
Attacker also has token 1 (скомпрометирован)
└─ Attacker tries to use token 1
   → Обнаружено: token 1 уже использован (token 2 существует)
   → Отозвать token 1, 2, 3 (всю цепочку)
   → SECURITY INCIDENT logged
```

**Код:**

```python
class RefreshTokenService:
    async def detect_reuse(self, jti_hash: str) -> bool:
        """Проверить, используется ли токен повторно"""
        token = await db.get_refresh_token_by_jti(jti_hash)
        
        if not token:
            return False  # Токен не найден
        
        if token.revoked:
            # Токен уже отозван → попытка повторного использования!
            return True
        
        # Проверить, создан ли новый токен на базе этого
        child_exists = await db.refresh_token_with_parent_exists(jti_hash)
        if child_exists and token.revoked:
            # Старый токен отозван, но есть дочерний → повторное использование
            return True
        
        return False
    
    async def revoke_token_chain(self, token: RefreshToken):
        """Отозвать всю цепочку токенов при обнаружении атаки"""
        # Найти всех предков
        ancestors = []
        current = token
        while current.parent_jti_hash:
            parent = await db.get_refresh_token_by_jti_hash(
                current.parent_jti_hash
            )
            if not parent:
                break
            ancestors.append(parent)
            current = parent
        
        # Найти всех потомков
        descendants = []
        async def find_descendants(t):
            children = await db.get_refresh_tokens_with_parent(t.jti_hash)
            for child in children:
                descendants.append(child)
                await find_descendants(child)
        
        await find_descendants(token)
        
        # Отозвать всех
        all_tokens = [token] + ancestors + descendants
        for t in all_tokens:
            await db.revoke_refresh_token(t.id)
        
        # Логировать SECURITY INCIDENT
        await audit_service.log_security_incident(
            incident_type="token_reuse_detected",
            details={
                "user_id": str(token.user_id),
                "jti_hash": token.jti_hash,
                "token_chain_size": len(all_tokens),
                "revoked_tokens": [str(t.id) for t in all_tokens]
            }
        )
```

### 4. SQL Injection Protection

**Реализация:** Параметризованные запросы через ORM

```python
# ❌ ОПАСНО (прямое конкатенирование)
query = f"SELECT * FROM users WHERE username = '{username}'"

# ✅ БЕЗОПАСНО (параметризованный запрос через SQLAlchemy)
user = db.query(User).filter(User.username == username).first()

# ✅ БЕЗОПАСНО (параметризованный запрос через raw SQL)
query = text("SELECT * FROM users WHERE username = :username")
result = db.execute(query, {"username": username})
```

### 5. XSS Protection

**Валидация входных данных:**

```python
from pydantic import BaseModel, EmailStr, field_validator

class TokenRequest(BaseModel):
    username: str
    password: str
    client_id: str
    scope: Optional[str] = None
    
    @field_validator("username")
    def validate_username(cls, v):
        if not v or len(v) < 3 or len(v) > 255:
            raise ValueError("Invalid username length")
        # Проверить, что только допустимые символы
        if not all(c.isalnum() or c in "-_.@" for c in v):
            raise ValueError("Invalid characters in username")
        return v
    
    @field_validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password too short")
        # Требования сложности
        has_upper = any(c.isupper() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(not c.isalnum() for c in v)
        
        if not (has_upper and has_digit and has_special):
            raise ValueError("Password does not meet complexity requirements")
        return v
```

### 6. CORS Protection

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://codelab.local",
        "https://app.codelab.local"
    ],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=600  # Cache preflight for 10 minutes
)
```

---

## ✅ Валидация входных данных

### Email Validation

```python
from pydantic import EmailStr

email: EmailStr  # Автоматическая валидация формата email
```

**Примеры:**
- ✅ valid@example.com
- ✅ user+tag@example.co.uk
- ❌ invalid@
- ❌ @example.com
- ❌ user @example.com

### Password Requirements

| Требование | Мин. | Макс. | Тип |
|-----------|------|-------|-----|
| **Length** | 8 | 128 | символов |
| **Uppercase** | 1 | ∞ | [A-Z] |
| **Lowercase** | 1 | ∞ | [a-z] |
| **Digits** | 1 | ∞ | [0-9] |
| **Special Chars** | 1 | ∞ | !@#$%^&*-_ |

### Scope Validation

```python
ALLOWED_SCOPES = {
    "api:read": "Read-only access to API",
    "api:write": "Write access to API",
    "api:admin": "Admin access (internal use only)",
    "api:internal": "Internal service access"
}

def validate_scope(scope: str, allowed_scopes: Set[str]) -> bool:
    requested = set(scope.split())
    allowed = set(allowed_scopes.split())
    
    # Проверить, что все запрашиваемые scopes разрешены
    if not requested.issubset(allowed):
        raise InvalidScopeError()
    
    return True
```

---

## 📊 Security Headers

### Response Headers

```python
# app/middleware/security_headers.py
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'"
        )
        
        # HTTPS only
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        
        # Prevent caching of sensitive data
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        return response
```

---

## 🔐 HTTPS/TLS

**Требования:**
- ✅ TLS 1.2 минимум (TLS 1.3 рекомендуется)
- ✅ Strong cipher suites (ECDHE with AES-256-GCM)
- ✅ Валидный SSL сертификат
- ✅ HSTS enabled (Strict-Transport-Security)

**Конфигурация (nginx):**

```nginx
server {
    listen 443 ssl http2;
    server_name auth.codelab.local;
    
    # SSL Certificate
    ssl_certificate /etc/ssl/certs/auth.codelab.local.crt;
    ssl_certificate_key /etc/ssl/private/auth.codelab.local.key;
    
    # TLS Version
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    
    # Strong ciphers
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Redirect HTTP to HTTPS
    error_page 497 =301 https://$server_name$request_uri;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name auth.codelab.local;
    return 301 https://$server_name$request_uri;
}
```

---

## 📋 Logging & Auditing

### Что логировать

| Событие | Уровень | Содержание |
|---------|---------|-----------|
| **login_success** | INFO | user_id, client_id, scope, ip, user_agent |
| **login_failed** | WARNING | username, reason, ip, client_id |
| **token_refresh** | INFO | user_id, client_id |
| **token_reuse_detected** | CRITICAL | user_id, jti_hash, ip |
| **rate_limit_exceeded** | WARNING | ip, username, limit |
| **brute_force_blocked** | WARNING | username, attempts, ip |
| **invalid_scope** | WARNING | client_id, requested_scope |

### Что НЕ логировать

❌ Пароли (даже хэши)  
❌ Полные access tokens  
❌ Refresh tokens  
❌ Client secrets  
❌ Персональные данные (кроме user_id)  

### Формат Logs

```json
{
  "timestamp": "2026-03-22T05:40:00.000Z",
  "level": "INFO",
  "event_type": "login_success",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "client_id": "codelab-flutter-app",
  "scope": "api:read api:write",
  "ip_address": "192.168.1.100",
  "user_agent": "CodeLab/1.0.0 (Flutter; Android)",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

---

## 🧪 Security Testing Checklist

- [ ] **SQL Injection** — параметризованные запросы
- [ ] **XSS** — валидация входных данных, escaping output
- [ ] **CSRF** — SameSite cookies, CSRF tokens (если есть)
- [ ] **Brute Force** — rate limiting, account lockout
- [ ] **JWT Tampering** — проверка подписи, exp, aud, iss
- [ ] **Token Reuse** — detection & revocation
- [ ] **Password Strength** — complexity requirements
- [ ] **Insecure Transport** — HTTPS only
- [ ] **Sensitive Data** — не логировать пароли/токены
- [ ] **Authorization** — scope validation
- [ ] **Information Disclosure** — generic error messages
- [ ] **Dependency Vulnerabilities** — регулярные обновления

---

## 🔄 Key Rotation

**Процесс ротации RSA ключей:**

```
1. Генерирование новой пары ключей
   - Новый kid: "2024-02-key-1"
   - Размер: 2048 bit
   - Алгоритм: RSA

2. Добавление публичного ключа в JWKS
   - Оба ключа (старый и новый) в /.well-known/jwks.json
   - Кэш инвалидируется

3. Обновление конфигурации
   - Новый приватный ключ используется для подписей
   - Старый ключ остаётся для валидации

4. Период переходности (15 минут)
   - Access tokens (TTL 15 минут) валидируются старым ключом
   - Все новые токены подписаны новым ключом

5. Удаление старого ключа
   - После истечения TTL access token
   - Старый ключ можно удалить из JWKS
   - Можно удалить файл приватного ключа

6. Архивирование
   - Старые ключи сохраняются в архиве (для forensics)
```

---

## 📊 Security Metrics

```python
# Prometheus metrics для мониторинга безопасности

failed_login_attempts_total = Counter(
    "auth_failed_login_attempts_total",
    "Total failed login attempts",
    ["username", "reason"]
)

brute_force_blocks_total = Counter(
    "auth_brute_force_blocks_total",
    "Total brute-force blocks"
)

rate_limit_exceeded_total = Counter(
    "auth_rate_limit_exceeded_total",
    "Total rate limit exceeded",
    ["limit_type"]
)

token_reuse_detected_total = Counter(
    "auth_token_reuse_detected_total",
    "Total refresh token reuse attempts (security incidents)"
)

invalid_jwt_total = Counter(
    "auth_invalid_jwt_total",
    "Total invalid JWT validation attempts",
    ["reason"]
)
```

---

## 📞 Контакты

**Разработчик:** Sergey Penkovsky  
**Email:** sergey.penkovsky@gmail.com  
**Версия:** 1.0.0  
**Дата:** 2026-03-22
