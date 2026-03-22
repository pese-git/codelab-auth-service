# Архитектурная спецификация Auth Service

**Версия:** 1.0.0  
**Статус:** ✅ Production Ready  
**Дата обновления:** 22 марта 2026

---

## 🏗️ Обзор архитектуры

CodeLab Auth Service построен на принципах **Layered Architecture** с четкой разделением ответственности между слоями. Сервис спроектирован как **stateless** микросервис, позволяющий горизонтальное масштабирование.

### Архитектурные пильлары

- ✅ **Layered Architecture** — четкие слои ответственности
- ✅ **Dependency Injection** — слабая связанность компонентов
- ✅ **Stateless Design** — горизонтальное масштабирование
- ✅ **Separation of Concerns** — логика разделена по файлам и модулям

---

## 📊 Слои архитектуры

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer                            │
│  - FastAPI endpoints                                    │
│  - Request/Response validation                          │
│  - HTTP status codes                                    │
└─────────────────┬───────────────────────────────────────┘
                  │ Pydantic schemas
                  ▼
┌─────────────────────────────────────────────────────────┐
│                 Service Layer                           │
│  - AuthService (бизнес-логика аутентификации)          │
│  - TokenService (создание/валидация JWT)               │
│  - UserService (управление пользователями)             │
│  - OAuthClientService (валидация клиентов)             │
│  - RefreshTokenService (управление refresh токенами)   │
│  - RateLimiterService (ограничение частоты запросов)   │
│  - BruteForceProtectionService (защита от перебора)    │
│  - AuditService (логирование событий)                  │
│  - JWKSService (управление публичными ключами)         │
└─────────────────┬───────────────────────────────────────┘
                  │ Repository pattern
                  ▼
┌─────────────────────────────────────────────────────────┐
│              Repository/Model Layer                     │
│  - SQLAlchemy ORM models                               │
│  - User, OAuthClient, RefreshToken, AuditLog           │
│  - Database queries & persistence                      │
└─────────────────┬───────────────────────────────────────┘
                  │
        ┌─────────┴──────────┬──────────────┐
        ▼                    ▼              ▼
   ┌─────────┐          ┌──────────┐  ┌─────────┐
   │ SQLite  │          │PostgreSQL│  │  Redis  │
   │ (Dev)   │          │ (Prod)   │  │(Cache)  │
   └─────────┘          └──────────┘  └─────────┘
```

### 1️⃣ API Layer (`app/api/`)

**Ответственность:** Обработка HTTP запросов и формирование ответов

```python
# app/api/v1/oauth.py — OAuth2 endpoints
- POST /oauth/token          # Выдача токенов
- POST /oauth/revoke         # Отзыв токенов (опционально)

# app/api/v1/jwks.py — JWKS endpoint
- GET /.well-known/jwks.json # Публичные ключи

# app/main.py — Health check
- GET /health                # Статус сервиса
```

**Ключевые компоненты:**
- FastAPI Router для группировки endpoints
- Pydantic schemas для валидации
- Dependency Injection (Depends)
- OAuth2 error responses (RFC 6749)

### 2️⃣ Service Layer (`app/services/`)

**Ответственность:** Бизнес-логика приложения

```python
# Основные сервисы:
├── AuthService              # Аутентификация пользователей
├── TokenService             # Создание/валидация JWT
├── UserService              # Управление пользователями
├── OAuthClientService       # Валидация OAuth клиентов
├── RefreshTokenService      # Управление refresh токенами
├── RateLimiterService       # Rate limiting (Redis)
├── BruteForceProtectionService  # Защита от перебора
├── AuditService             # Логирование событий
└── JWKSService              # Управление публичными ключами
```

**Принципы:**
- Каждый сервис отвечает за одну область
- Сервисы используют друг друга (composition)
- Внешние зависимости инъектируются
- Логика сервиса не зависит от HTTP

### 3️⃣ Model/Repository Layer (`app/models/`)

**Ответственность:** Работа с данными через ORM

```python
# SQLAlchemy ORM модели:
├── User                     # Таблица users
├── OAuthClient              # Таблица oauth_clients
├── RefreshToken             # Таблица refresh_tokens
└── AuditLog                 # Таблица audit_logs
```

**Database Session Management:**
```python
# app/core/dependencies.py
@dependency
def get_db() -> Generator[Session, None, None]:
    """Dependency для получения сессии БД"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

### 4️⃣ Infrastructure Layer

**Redis:**
- Rate limiting счетчики
- JWKS кэш
- OAuth client кэш
- Blacklist отозванных токенов

**Database:**
- Хранение пользователей
- Хранение refresh токенов (хэш jti)
- Аудит логи

---

## 🔄 Поток данных

### OAuth2 Password Grant flow

```
Client
  │ 1. POST /oauth/token
  │    (username, password, client_id)
  ▼
API Layer (oauth.py)
  │ 2. Валидация параметров
  ▼
AuthService.authenticate()
  │ 3. Проверка rate limiting
  ├─→ RateLimiterService.check_rate_limit(ip, username)
  │
  │ 4. Проверка brute-force
  ├─→ BruteForceProtectionService.check_attempts(username)
  │
  │ 5. Поиск пользователя
  ├─→ UserService.get_by_username()
  │    └─→ Model Layer (User.query)
  │
  │ 6. Проверка пароля (bcrypt constant-time)
  ├─→ UserService.verify_password()
  │
  │ 7. Валидация OAuth клиента
  ├─→ OAuthClientService.validate_client()
  │
  │ 8. Валидация scope
  ├─→ OAuthClientService.validate_scope()
  │
  │ 9. Создание токенов
  ├─→ TokenService.create_access_token()
  ├─→ TokenService.create_refresh_token()
  │
  │ 10. Сохранение refresh token
  ├─→ RefreshTokenService.save_refresh_token()
  │    └─→ Model Layer (RefreshToken.save)
  │
  │ 11. Логирование события
  ├─→ AuditService.log_login_success()
  │    └─→ Model Layer (AuditLog.save)
  │
  │ 12. Обновление last_login
  ├─→ UserService.update_last_login()
  ▼
API Layer
  │ 13. Формирование ответа
  ▼
Client
  │ {
  │   "access_token": "...",
  │   "refresh_token": "...",
  │   "token_type": "bearer",
  │   "expires_in": 900
  │ }
```

### Refresh Token Grant flow

```
Client
  │ 1. POST /oauth/token
  │    (grant_type=refresh_token, refresh_token, client_id)
  ▼
API Layer
  │ 2. Валидация параметров
  ▼
TokenService.validate_and_decode_refresh_token()
  │ 3. Парсинг JWT
  ├─→ jwt.decode() — валидация подписи RS256
  │
  │ 4. Проверка типа токена
  ├─→ payload.get("type") == "refresh"
  │
  │ 5. Проверка в БД (jti_hash)
  ├─→ RefreshTokenService.get_by_jti()
  │    └─→ Model Layer (RefreshToken.query)
  │
  │ 6. Проверка на revoked
  ├─→ if refresh_token.revoked: raise InvalidGrantError()
  │
  │ 7. Проверка на reuse detection
  ├─→ RefreshTokenService.detect_reuse()
  │    └─→ Если обнаружено повторное использование:
  │        - Отозвать всю цепочку токенов
  │        - Залогировать security incident
  │
  │ 8. Создание новых токенов
  ├─→ TokenService.create_access_token()
  ├─→ TokenService.create_refresh_token()
  │
  │ 9. Ротация refresh token
  ├─→ Старый токен отзывается
  ├─→ Новый сохраняется с parent_jti_hash
  │    └─→ RefreshTokenService.save_refresh_token()
  │
  │ 10. Логирование
  ├─→ AuditService.log_token_refresh()
  ▼
API Layer
  │ 11. Формирование ответа
  ▼
Client
```

---

## 🧩 Компоненты системы

### 1. Security Core (`app/core/security.py`)

```python
class SecurityCore:
    # RSA ключи
    - private_key: RSA private key
    - public_keys: Dict[kid] -> RSA public key
    - current_key_id: str
    
    # Методы
    - load_keys() → загрузка из файловой системы
    - rotate_keys() → ротация ключей
    - get_jwks() → формирование JWKS объекта
```

**Особенности:**
- Поддержка множественных ключей (для rotation)
- Загрузка при старте приложения
- Кэширование в Redis

### 2. Token Service (`app/services/token_service.py`)

```python
class TokenService:
    def create_access_token(
        user_id: UUID,
        client_id: str,
        scope: str,
        lifetime: int = 900
    ) -> str:
        # JWT payload
        payload = {
            "iss": "https://auth.codelab.local",
            "sub": str(user_id),
            "aud": "codelab-api",
            "exp": now + lifetime,
            "iat": now,
            "scope": scope,
            "jti": str(uuid.uuid4()),
            "type": "access",
            "client_id": client_id
        }
        # Подпись RS256
        return jwt.encode(payload, private_key, "RS256")
    
    def create_refresh_token(...) -> str:
        # Аналогично, но type="refresh"
        # Сохраняется в БД после создания
    
    def validate_and_decode_access_token(token: str) -> dict:
        # Валидация подписи и сроков
        # Проверка type="access"
        return jwt.decode(token, public_key, "RS256")
    
    def validate_and_decode_refresh_token(token: str) -> dict:
        # Валидация подписи
        # Проверка в БД (jti_hash)
        # Проверка на revoked
```

### 3. User Service (`app/services/user_service.py`)

```python
class UserService:
    def create_user(username: str, email: str, password: str) -> User:
        # Валидация email и пароля
        # bcrypt хэширование (cost=12)
        # Сохранение в БД
    
    def get_by_username(username: str) -> Optional[User]:
        # Query с кэшированием (Redis, TTL=1min)
    
    def get_by_email(email: str) -> Optional[User]:
        # Аналогично
    
    def verify_password(user: User, password: str) -> bool:
        # Constant-time сравнение (bcrypt)
    
    def update_last_login(user_id: UUID):
        # Обновление timestamp
```

### 4. OAuth Client Service (`app/services/oauth_client_service.py`)

```python
class OAuthClientService:
    def get_client(client_id: str) -> Optional[OAuthClient]:
        # Query с кэшированием (Redis, TTL=5min)
    
    def validate_scope(client: OAuthClient, scope: str) -> bool:
        # Проверка, что scope входит в allowed_scopes
    
    def validate_grant_type(client: OAuthClient, grant_type: str) -> bool:
        # Проверка, что grant_type в allowed_grant_types
```

### 5. Refresh Token Service (`app/services/refresh_token_service.py`)

```python
class RefreshTokenService:
    def save_refresh_token(
        user_id: UUID,
        client_id: str,
        jti: str,
        scope: str,
        lifetime: int,
        parent_jti_hash: Optional[str] = None
    ) -> RefreshToken:
        # Сохранение хэша jti (SHA-256)
        # Привязка к пользователю и клиенту
        # Отслеживание цепочки (parent_jti_hash)
    
    def get_by_jti_hash(jti_hash: str) -> Optional[RefreshToken]:
        # Query по хэшированному jti
    
    def revoke_token(refresh_token: RefreshToken):
        # Пометка как revoked
    
    def detect_reuse(jti_hash: str) -> bool:
        # Если токен уже использован → reuse attack
        # Отозвать цепочку, залогировать
    
    def revoke_token_chain(refresh_token: RefreshToken):
        # Отозвать все токены в цепочке (обнаружение атак)
```

### 6. Rate Limiter Service (`app/services/rate_limiter.py`)

```python
class RateLimiterService:
    def check_rate_limit(ip: str, username: Optional[str] = None) -> bool:
        # Redis ключи:
        # rate_limit:ip:{ip} — 5 req/min
        # rate_limit:username:{username} — 10 req/hour
        
        if ip_count > 5:
            raise RateLimitError()
        if username_count > 10:
            raise RateLimitError()
        
        return True
```

### 7. Brute Force Protection (`app/services/brute_force_protection.py`)

```python
class BruteForceProtectionService:
    def check_attempts(username: str) -> bool:
        # Redis ключ: brute_force:{username}
        # Счетчик неудачных попыток
        
        if attempts >= 5:
            # Заблокировать на 15 минут
            raise AccountLockedError()
    
    def record_failed_attempt(username: str):
        # Инкрементировать счетчик
    
    def clear_attempts(username: str):
        # Сбросить счетчик (после успешного входа)
```

### 8. Audit Service (`app/services/audit_service.py`)

```python
class AuditService:
    def log_login_success(
        user_id: UUID,
        client_id: str,
        ip_address: str,
        user_agent: str,
        scope: str
    ):
        # Сохранить в БД с JSON event_data
    
    def log_login_failed(
        username: str,
        reason: str,
        ip_address: str,
        client_id: str
    ):
        # Логирование неудачной попытки
    
    def log_token_refresh(user_id: UUID, client_id: str):
        # Логирование обновления токена
    
    def log_security_incident(
        incident_type: str,
        details: dict,
        user_id: Optional[UUID] = None
    ):
        # Критические события (reuse attack, etc.)
```

### 9. JWKS Service (`app/services/jwks_service.py`)

```python
class JWKSService:
    def get_jwks() -> dict:
        # Получить из кэша (Redis)
        # Если не в кэше:
        # - Получить публичные ключи (security_core)
        # - Сформировать JWKS JSON
        # - Кэшировать (TTL=1h)
        # - Вернуть
    
    def get_jwks_formatted() -> JWKSResponse:
        # Возвращает в формате RFC 7517
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "kid": "2024-01-key-1",
                    "alg": "RS256",
                    "n": "...",
                    "e": "AQAB"
                }
            ]
        }
```

---

## 🔌 Middleware

### Logging Middleware (`app/middleware/logging.py`)

```python
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Добавить correlation ID
        request.state.correlation_id = uuid.uuid4()
        
        # Логирование входящего запроса
        logger.info(
            "Incoming request",
            extra={
                "correlation_id": request.state.correlation_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host
            }
        )
        
        # Выполнить запрос
        response = await call_next(request)
        
        # Логирование ответа
        logger.info(
            "Request completed",
            extra={
                "correlation_id": request.state.correlation_id,
                "status_code": response.status_code,
                "duration_ms": ...
            }
        )
        
        return response
```

### Rate Limit Middleware (`app/middleware/rate_limit.py`)

```python
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Применить rate limiting к /oauth/token
        if request.url.path == "/oauth/token":
            ip = request.client.host
            
            if not await rate_limiter.check_rate_limit(ip):
                return JSONResponse(
                    status_code=429,
                    content={"error": "rate_limit_exceeded"}
                )
        
        return await call_next(request)
```

---

## 🔗 Диаграмма взаимодействия компонентов

```
┌─────────────┐
│   FastAPI   │  HTTP endpoints
└──────┬──────┘
       │
       ▼
┌──────────────────────────────┐
│   API Layer (routers)        │  Валидация запроса
├──────────────────────────────┤
│ - oauth.py (POST /oauth/token)
│ - jwks.py (GET /.well-known/jwks.json)
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│       Service Layer                      │
├──────────────────────────────────────────┤
│  AuthService ──┬─→ UserService          │  Бизнес-логика
│                ├─→ OAuthClientService   │
│                ├─→ TokenService         │
│                ├─→ RateLimiterService   │
│                ├─→ BruteForceService    │
│                ├─→ RefreshTokenService  │
│                ├─→ AuditService         │
│                └─→ JWKSService          │
└──────┬────────────────────────────────────┘
       │
       ├─────────────┬──────────────┬──────────┐
       ▼             ▼              ▼          ▼
    ┌────────┐  ┌──────────┐  ┌──────────┐ ┌─────────┐
    │ SQLite │  │PostgreSQL│  │  Redis   │ │  Crypto │
    │ (Dev)  │  │ (Prod)   │  │ (Cache)  │ │ (Keys)  │
    └────────┘  └──────────┘  └──────────┘ └─────────┘
```

---

## 📐 Design Patterns

### 1. Dependency Injection

```python
# app/core/dependencies.py
@dependency
def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    yield session
    session.close()

@dependency
def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)

# Использование
@router.post("/oauth/token")
async def token_endpoint(
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
):
    ...
```

### 2. Repository Pattern

```python
# app/models/user.py
class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True)
    username = Column(String(255), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    password_hash = Column(String(255))
    
    @classmethod
    def get_by_username(cls, session: Session, username: str):
        return session.query(cls).filter(cls.username == username).first()
```

### 3. Service Layer

```python
# app/services/user_service.py
class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_username(self, username: str) -> Optional[User]:
        return User.get_by_username(self.db, username)
```

### 4. Factory Pattern

```python
# Создание сервисов
def get_auth_service(db: Session) -> AuthService:
    user_service = UserService(db)
    token_service = TokenService()
    rate_limiter = RateLimiterService(redis_client)
    
    return AuthService(
        user_service=user_service,
        token_service=token_service,
        rate_limiter=rate_limiter,
        db=db
    )
```

---

## 🚀 Масштабирование

### Horizontal Scaling

```
┌────────────────────────────────────────┐
│         Load Balancer (nginx)          │
├────────────────────────────────────────┤
│                                        │
│  ┌──────────────┐  ┌──────────────┐   │
│  │Auth Service 1│  │Auth Service 2│   │  Stateless instances
│  │  (port 8003) │  │  (port 8004) │   │
│  └──────┬───────┘  └──────┬───────┘   │
│         │                  │           │
│  ┌──────────────┐  ┌──────────────┐   │
│  │Auth Service N│  │ Load Balanced│   │
│  │  (port XXXX) │  │   Requests   │   │
│  └──────┬───────┘  └──────┬───────┘   │
│         │                  │           │
└─────────┼──────────────────┼───────────┘
          │                  │
          └────────┬─────────┘
                   ▼
          ┌────────────────┐
          │  PostgreSQL    │  Shared state
          │   (Primary)    │
          └────────────────┘
          ┌────────────────┐
          │   Redis        │  Cache & Rate Limiting
          │   (Cluster)    │
          └────────────────┘
```

**Условия для масштабирования:**
- ✅ Access tokens stateless (не хранятся в БД)
- ✅ Refresh tokens в общей БД
- ✅ Redis для rate limiting и кэша
- ✅ Load balancer распределяет нагрузку

### Caching Strategy

```
┌────────────────────────────────────────┐
│        Application Layer               │
├────────────────────────────────────────┤
│                                        │
│  L1 Cache (In-Memory):                 │
│  - User lookups (TTL=1min)             │
│  - OAuth clients (TTL=5min)            │
│  - JWKS (TTL=1h)                       │
│                                        │
│  ↓ Cache miss                          │
│                                        │
│  L2 Cache (Redis):                     │
│  - User lookups (TTL=5min)             │
│  - OAuth clients (TTL=10min)           │
│  - JWKS (TTL=1h)                       │
│  - Rate limit counters (TTL=60sec)     │
│  - Brute force counters (TTL=15min)    │
│                                        │
│  ↓ Cache miss                          │
│                                        │
│  L3 Storage (Database):                │
│  - PostgreSQL queries                  │
│                                        │
└────────────────────────────────────────┘
```

---

## 🔐 Security Architecture

### Key Management

```
┌──────────────────────────────────────┐
│   RSA Key Pair Generation            │
│   (2048 bit, RS256)                  │
├──────────────────────────────────────┤
│                                      │
│  Private Key ──────────────→ Storage │  /app/keys/private_key.pem
│  (Signing tokens)          (secure)  │  - Only readable by app
│  (Keep secret!)            (volume)  │  - Mounted read-only
│                                      │
│  Public Key ───────────────→ JWKS    │  /.well-known/jwks.json
│  (Verifying tokens)        (cached)  │  - Cached in Redis
│  (Distribute to clients)   (endpoint)│  - Cached 1 hour
│                                      │
└──────────────────────────────────────┘
```

### Token Validation Flow

```
┌──────────────────────────────────────────┐
│  Client sends: Authorization: Bearer {token}
└──────────┬───────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│  Extract token from header               │
└──────────┬───────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│  Parse JWT (decode, no verification)     │
│  Extract: header, payload, signature     │
└──────────┬───────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│  Get public key using kid from header    │
│  (from cache or JWKS endpoint)           │
└──────────┬───────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│  Verify signature using RS256 algorithm  │
│  (constant-time, RSA 2048-bit)           │
└──────────┬───────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│  Check token expiration (exp claim)      │
└──────────┬───────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│  Check audience (aud claim)              │
│  Check issuer (iss claim)                │
└──────────┬───────────────────────────────┘
           │
           ▼
✅ Token valid → Extract user_id and scope
```

---

## 📞 Контакты

**Разработчик:** Sergey Penkovsky  
**Email:** sergey.penkovsky@gmail.com  
**Версия:** 1.0.0  
**Дата:** 2026-03-22
