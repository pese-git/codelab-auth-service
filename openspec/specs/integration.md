# Спецификация интеграций

**Версия:** 1.0.0  
**Статус:** ✅ Production Ready  
**Дата обновления:** 22 марта 2026

---

## 🔗 Обзор интеграций

Auth Service интегрируется с существующей микросервисной архитектурой CodeLab, обеспечивая централизованную аутентификацию и авторизацию для всех сервисов.

**Интегрируемые компоненты:**
- ✅ **Gateway** — валидация JWT токенов
- ✅ **Agent Runtime** — JWT валидация и привязка user_id
- ✅ **LLM Proxy** — опциональная JWT интеграция
- ✅ **Redis** — кэширование и rate limiting
- ✅ **PostgreSQL/SQLite** — хранение данных

---

## 🌉 Интеграция с Gateway

### Текущее состояние

Gateway использует `InternalAuthMiddleware` с единым API ключом:

```python
# ТЕКУЩЕЕ (до интеграции)
class InternalAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("X-Internal-Auth")
        if auth_header != AppConfig.INTERNAL_API_KEY:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        return await call_next(request)
```

### Требуемые изменения

#### 1. Добавить зависимость

```toml
# gateway/pyproject.toml
dependencies = [
    # ... существующие
    "python-jose[cryptography]==3.3.0",
]
```

#### 2. Создать JWT Auth Middleware

```python
# gateway/app/middleware/jwt_auth.py
from jose import jwt, JWTError
import httpx
import time
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class JWTAuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        jwks_url: str,
        cache_ttl: int = 3600,
        public_paths: list = None
    ):
        super().__init__(app)
        self.jwks_url = jwks_url
        self.cache_ttl = cache_ttl
        self.jwks_cache = None
        self.jwks_cache_time = 0
        self.public_paths = public_paths or []
    
    async def get_jwks(self):
        """Получить JWKS с кэшированием (TTL 1 час)"""
        current_time = time.time()
        
        # Проверить кэш
        if self.jwks_cache and (current_time - self.jwks_cache_time) < self.cache_ttl:
            return self.jwks_cache
        
        # Загрузить из Auth Service
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.jwks_url)
                response.raise_for_status()
                self.jwks_cache = response.json()
                self.jwks_cache_time = current_time
                logger.info("JWKS updated from Auth Service")
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            if self.jwks_cache:
                # Использовать старый кэш при ошибке
                return self.jwks_cache
            raise
        
        return self.jwks_cache
    
    async def dispatch(self, request: Request, call_next):
        # Пропустить публичные paths
        if request.url.path in self.public_paths:
            return await call_next(request)
        
        # Извлечь токен из заголовка
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.warning(f"Missing or invalid Authorization header from {request.client.host}")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "unauthorized",
                    "error_description": "Missing or invalid Authorization header"
                }
            )
        
        token = auth_header[7:]  # Удалить "Bearer "
        
        try:
            # Получить JWKS
            jwks = await self.get_jwks()
            
            # Декодировать и валидировать JWT
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                audience="codelab-api",
                options={"verify_exp": True}
            )
            
            # Проверить тип токена
            if payload.get("type") != "access":
                logger.warning(f"Invalid token type from {request.client.host}")
                return JSONResponse(
                    status_code=401,
                    content={"error": "invalid_token", "error_description": "Invalid token type"}
                )
            
            # Добавить user_id и scope в request.state
            request.state.user_id = payload["sub"]
            request.state.scope = payload.get("scope", "")
            request.state.client_id = payload.get("client_id")
            request.state.jti = payload.get("jti")
            
            logger.info(
                f"JWT validated successfully",
                extra={
                    "user_id": request.state.user_id,
                    "client_id": request.state.client_id
                }
            )
            
        except JWTError as e:
            logger.error(f"JWT validation failed: {e}")
            return JSONResponse(
                status_code=401,
                content={"error": "invalid_token", "error_description": str(e)}
            )
        except Exception as e:
            logger.error(f"Unexpected error during JWT validation: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": "server_error"}
            )
        
        return await call_next(request)
```

#### 3. Обновить конфигурацию

```python
# gateway/app/core/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class AppConfig(BaseSettings):
    # Существующие настройки
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # Auth Service
    AUTH_SERVICE_URL: str = "http://auth-service:8003"
    JWKS_URL: Optional[str] = None
    
    # JWT Auth
    USE_JWT_AUTH: bool = False
    JWT_CACHE_TTL: int = 3600  # 1 hour
    
    # Public paths (не требуют JWT)
    PUBLIC_PATHS: list = [
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc"
    ]
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.JWKS_URL:
            self.JWKS_URL = f"{self.AUTH_SERVICE_URL}/.well-known/jwks.json"
```

#### 4. Интегрировать middleware в приложение

```python
# gateway/app/main.py
from fastapi import FastAPI
from app.middleware.jwt_auth import JWTAuthMiddleware
from app.middleware.internal_auth import InternalAuthMiddleware
from app.core.config import AppConfig

app = FastAPI(title="CodeLab Gateway")
config = AppConfig()

# Выбрать middleware в зависимости от конфигурации
if config.USE_JWT_AUTH:
    app.add_middleware(
        JWTAuthMiddleware,
        jwks_url=config.JWKS_URL,
        cache_ttl=config.JWT_CACHE_TTL,
        public_paths=config.PUBLIC_PATHS
    )
else:
    # Переходный период: использовать InternalAuthMiddleware
    app.add_middleware(InternalAuthMiddleware)

# ... остальное приложение
```

#### 5. Использование user_id в endpoints

```python
# gateway/app/api/v1/endpoints.py
from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/chat")
async def chat(request: Request, message: ChatMessage):
    # Извлечь user_id из JWT
    user_id = getattr(request.state, "user_id", None)
    scope = getattr(request.state, "scope", "")
    client_id = getattr(request.state, "client_id", None)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Использовать user_id для логики
    response = await agent_runtime_service.process_message(
        user_id=user_id,
        message=message.content,
        scope=scope
    )
    
    return response
```

---

## 🌉 Интеграция с Agent Runtime

### Текущее состояние

Agent Runtime использует `InternalAuthMiddleware` и не имеет привязки к пользователям:

```python
# ТЕКУЩЕЕ (до интеграции)
class Session(Base):
    __tablename__ = "sessions"
    id = Column(String(36), primary_key=True)
    # Нет user_id!
```

### Требуемые изменения

#### 1. Добавить зависимость и middleware

Аналогично Gateway (см. выше).

#### 2. Обновить модели

```python
# agent-runtime/app/models/session.py
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from datetime import datetime

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)  # НОВОЕ ПОЛЕ
    agent_id = Column(String(36), nullable=False)
    state = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Составной индекс для быстрого поиска
    __table_args__ = (
        Index('idx_session_user_id_agent_id', 'user_id', 'agent_id'),
    )
```

#### 3. Создать миграцию

```python
# agent-runtime/alembic/versions/XXX_add_user_id_to_sessions.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Добавить колонку
    op.add_column(
        'sessions',
        sa.Column('user_id', sa.String(36), nullable=True)
    )
    
    # Создать индекс
    op.create_index('idx_sessions_user_id', 'sessions', ['user_id'])
    
    # Заполнить existing rows с default user_id
    op.execute("UPDATE sessions SET user_id = 'system' WHERE user_id IS NULL")
    
    # Сделать колонку NOT NULL
    op.alter_column('sessions', 'user_id', nullable=False)

def downgrade():
    op.drop_index('idx_sessions_user_id', 'sessions')
    op.drop_column('sessions', 'user_id')
```

#### 4. Обновить SessionManager

```python
# agent-runtime/app/services/session_manager.py
from app.models.session import Session
from sqlalchemy.orm import Session as DBSession

class SessionManager:
    def __init__(self, db: DBSession):
        self.db = db
    
    async def create_session(
        self,
        user_id: str,
        agent_id: str,
        state: dict = None
    ) -> Session:
        """Создать новую сессию привязанную к пользователю"""
        session = Session(
            id=str(uuid.uuid4()),
            user_id=user_id,  # Привязка к пользователю
            agent_id=agent_id,
            state=state or {}
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session
    
    async def get_user_sessions(self, user_id: str) -> list:
        """Получить все сессии пользователя"""
        return self.db.query(Session).filter(
            Session.user_id == user_id
        ).all()
    
    async def get_session(self, session_id: str, user_id: str) -> Optional[Session]:
        """Получить сессию с проверкой владельца"""
        return self.db.query(Session).filter(
            Session.id == session_id,
            Session.user_id == user_id  # Безопасность: только свои сессии
        ).first()
    
    async def delete_user_sessions(self, user_id: str):
        """Удалить все сессии пользователя (например, при logout)"""
        self.db.query(Session).filter(
            Session.user_id == user_id
        ).delete()
        self.db.commit()
```

---

## 🌉 Интеграция с LLM Proxy

### Текущее состояние

LLM Proxy используется только внутренними сервисами (Agent Runtime).

### Опции

#### Опция 1: Оставить внутреннюю аутентификацию (Рекомендуется для MVP)

```python
# LLM Proxy остаётся с X-Internal-Auth
# Используется только внутри платформы
# Gateway и Agent Runtime используют X-Internal-Auth для обращений к LLM Proxy

# agent-runtime/services/llm_client.py
async def call_llm(prompt: str):
    headers = {
        "X-Internal-Auth": config.INTERNAL_API_KEY,
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{config.LLM_PROXY_URL}/v1/completions",
            json={"prompt": prompt},
            headers=headers
        )
    return response.json()
```

#### Опция 2: Добавить JWT валидацию (Post-MVP)

Если требуется прямой доступ клиентов к LLM Proxy:

```python
# Добавить JWTAuthMiddleware
# Проверять scope "llm:access"
# Логировать использование по user_id
```

**Рекомендация:** Для MVP оставить внутреннюю аутентификацию.

---

## 📧 Интеграция с Email Service (Password Reset Notifications)

### Текущее состояние

Auth Service включает функциональность сброса пароля, которая отправляет email уведомления через SMTP.

### Требуемые зависимости

#### 1. SMTP Integration (email-notifications capability)

Password Reset Notifications зависит от существующей SMTP интеграции для отправки писем:

```python
# app/services/password_reset_notifications.py
from app.services.email_notifications import EmailNotificationService

class PasswordResetNotificationService:
    def __init__(self, email_service: EmailNotificationService):
        self.email_service = email_service
    
    async def send_password_reset_email(
        self,
        user_email: str,
        user_name: str,
        reset_token: str,
        reset_url: str
    ):
        """Отправить письмо с ссылкой сброса пароля"""
        
        # Подготовить переменные шаблона
        template_vars = {
            "user_name": user_name,
            "reset_url": reset_url,
            "token_expiry_hours": 0.5,  # 30 минут
            "support_email": "support@codelab.local",
            "current_year": datetime.now().year,
            "app_name": "CodeLab"
        }
        
        # Использовать email service для отправки
        await self.email_service.send_email(
            to_email=user_email,
            template_type="password_reset",
            template_vars=template_vars,
            retry_count=3
        )
```

#### 2. Email Templates (email-templates capability)

Требуется создание email шаблона для сброса пароля:

```
app/templates/emails/password_reset/
├── subject.txt          # Тема письма
├── template.html        # HTML версия
└── template.txt         # Текстовая версия
```

**Шаблон subject.txt:**
```
Восстановление доступа к вашему аккаунту CodeLab
```

**Переменные шаблона:**
- `user_name` — Имя пользователя
- `reset_url` — Полный URL с токеном
- `token_expiry_hours` — Часы до истечения (0.5 = 30 минут)
- `support_email` — Email поддержки
- `current_year` — Текущий год
- `app_name` — Название приложения

#### 3. Async Processing

Отправка письма должна быть асинхронной и не блокировать API ответ:

```python
# app/api/v1/password_reset.py
from fastapi import BackgroundTasks

@router.post("/auth/password-reset/request")
async def request_password_reset(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession
):
    # Найти пользователя
    user = await user_service.get_by_email(request.email)
    
    if user:
        # Генерировать токен
        token = secrets.token_urlsafe(32)
        
        # Сохранить в БД
        await password_reset_service.create_token(user.id, token)
        
        # Отправить письмо в background (не блокирует ответ)
        background_tasks.add_task(
            notification_service.send_password_reset_email,
            user_email=user.email,
            user_name=user.username,
            reset_token=token,
            reset_url=f"https://app.codelab.local/auth/reset-password?token={token}"
        )
    
    # Вернуть успех немедленно (не раскрывать существует ли пользователь)
    return {
        "status": "success",
        "message": "Инструкции по восстановлению пароля отправлены"
    }
```

#### 4. Retry Logic

Email Service должна иметь retry logic с exponential backoff:

```python
# app/services/email_retry.py
async def send_email_with_retry(
    to_email: str,
    template_type: str,
    template_vars: dict,
    max_retries: int = 3,
    base_delay: int = 1
):
    """Отправить email с retry логикой"""
    for attempt in range(max_retries):
        try:
            await smtp_client.send(
                to_email=to_email,
                subject=render_template(f"{template_type}_subject"),
                html_body=render_template(f"{template_type}_html", template_vars),
                text_body=render_template(f"{template_type}_txt", template_vars)
            )
            return True
        except SMTPException as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                await asyncio.sleep(delay)
            else:
                raise
```

---

## 🐳 Docker Compose интеграция

### Добавить Auth Service

```yaml
# docker-compose.yml
version: '3.8'

services:
  auth-service:
    build:
      context: ./auth-service
      dockerfile: Dockerfile
    ports:
      - "${AUTH_SERVICE_PORT:-8003}:8003"
    volumes:
      - ./auth-service/data:/app/data  # SQLite БД
      - ./auth-service/keys:/app/keys  # RSA ключи
    environment:
      - ENVIRONMENT=${ENVIRONMENT:-development}
      - PORT=8003
      - AUTH_SERVICE__DB_URL=sqlite:///data/auth.db
      - AUTH_SERVICE__REDIS_URL=redis://redis:6379/1
      - AUTH_SERVICE__LOG_LEVEL=${AUTH_SERVICE__LOG_LEVEL:-DEBUG}
      - AUTH_SERVICE__JWT_ISSUER=https://auth.codelab.local
      - AUTH_SERVICE__JWT_AUDIENCE=codelab-api
      - AUTH_SERVICE__ACCESS_TOKEN_LIFETIME=900
      - AUTH_SERVICE__REFRESH_TOKEN_LIFETIME=2592000
      - AUTH_SERVICE__PRIVATE_KEY_PATH=/app/keys/private_key.pem
      - AUTH_SERVICE__PUBLIC_KEY_PATH=/app/keys/public_key.pem
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - codelab-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s

  gateway:
    build:
      context: ./gateway
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=${ENVIRONMENT:-development}
      - GATEWAY__AUTH_SERVICE_URL=http://auth-service:8003
      - GATEWAY__USE_JWT_AUTH=${GATEWAY__USE_JWT_AUTH:-false}
    depends_on:
      agent-runtime:
        condition: service_healthy
      auth-service:
        condition: service_healthy
    networks:
      - codelab-network

  agent-runtime:
    build:
      context: ./agent-runtime
      dockerfile: Dockerfile
    ports:
      - "8001:8001"
    environment:
      - ENVIRONMENT=${ENVIRONMENT:-development}
      - AGENT_RUNTIME__AUTH_SERVICE_URL=http://auth-service:8003
      - AGENT_RUNTIME__USE_JWT_AUTH=${AGENT_RUNTIME__USE_JWT_AUTH:-false}
    depends_on:
      llm-proxy:
        condition: service_healthy
      auth-service:
        condition: service_healthy
    networks:
      - codelab-network

  llm-proxy:
    build:
      context: ./llm-proxy
      dockerfile: Dockerfile
    ports:
      - "8002:8002"
    networks:
      - codelab-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - codelab-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

networks:
  codelab-network:
    driver: bridge
```

### Обновить .env.example

```bash
# .env.example

# Environment
ENVIRONMENT=development

# Auth Service
AUTH_SERVICE_PORT=8003
AUTH_SERVICE__LOG_LEVEL=DEBUG

# Gateway
GATEWAY__USE_JWT_AUTH=false  # true для включения JWT (после тестирования)

# Agent Runtime
AGENT_RUNTIME__USE_JWT_AUTH=false  # true для включения JWT (после тестирования)
```

---

## 📋 Последовательность миграции

### Этап 1: Развертывание Auth Service (неделя 1-2)

- [ ] Развернуть Auth Service в Docker Compose
- [ ] Создать тестовых пользователей
- [ ] Протестировать OAuth2 flow (password grant)
- [ ] Убедиться, что JWKS endpoint работает
- [ ] Проверить rate limiting и brute-force protection

**Критерии завершения:**
- ✅ `curl http://localhost:8003/health` возвращает 200
- ✅ `curl http://localhost:8003/.well-known/jwks.json` возвращает JWKS
- ✅ Успешный login возвращает access и refresh токены

### Этап 2: Интеграция с Codelab Core Service (неделя 3)

- [ ] Добавить `JWTAuthMiddleware` в Codelab Core Service
- [ ] Обновить миграцию (добавить user_id в sessions)
- [ ] Обновить Chat Session, Providers, Projects (привязка к user_id)
- [ ] Тестирование привязки Chat Session, Providers, Projects к пользователям
- [ ] Переключить на JWT_AUTH

**Критерии завершения:**
- ✅ Chat Session, Providers, Projects привязаны к пользователям
- ✅ Пользователь может видеть только свои Chat Session, Providers, Projects
- ✅ JWT валидируется корректно

**Критерии завершения:**
- ✅ Все тесты проходят
- ✅ Нет ошибок в production
- ✅ Старый код полностью удалён

---

## 🧪 Тестирование интеграции

### Unit Tests

```python
# tests/test_jwt_middleware.py
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from app.middleware.jwt_auth import JWTAuthMiddleware

@pytest.fixture
def app_with_jwt():
    app = FastAPI()
    app.add_middleware(
        JWTAuthMiddleware,
        jwks_url="http://auth-service:8003/.well-known/jwks.json",
        public_paths=["/health"]
    )
    
    @app.get("/protected")
    async def protected(request: Request):
        return {"user_id": request.state.user_id}
    
    return app

def test_valid_jwt_token(app_with_jwt, valid_jwt_token):
    client = TestClient(app_with_jwt)
    response = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {valid_jwt_token}"}
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == "550e8400-e29b-41d4-a716-446655440000"

def test_missing_token(app_with_jwt):
    client = TestClient(app_with_jwt)
    response = client.get("/protected")
    assert response.status_code == 401

def test_invalid_token(app_with_jwt):
    client = TestClient(app_with_jwt)
    response = client.get(
        "/protected",
        headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert response.status_code == 401
```

### Integration Tests

```python
# tests/integration/test_full_auth_flow.py
import pytest
import httpx

@pytest.mark.asyncio
async def test_full_oauth_flow():
    """Test: Login → Get tokens → Use in Gateway → Refresh → Get new tokens"""
    
    async with httpx.AsyncClient() as client:
        # 1. Login (Password Grant)
        login_response = await client.post(
            "http://auth-service:8003/oauth/token",
            data={
                "grant_type": "password",
                "username": "test@example.com",
                "password": "password123",
                "client_id": "codelab-flutter-app",
                "scope": "api:read api:write"
            }
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        
        # 2. Use access token in Gateway
        gateway_response = await client.get(
            "http://gateway:8000/api/v1/user/profile",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert gateway_response.status_code == 200
        
        # 3. Refresh token (Refresh Token Grant)
        refresh_response = await client.post(
            "http://auth-service:8003/oauth/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": "codelab-flutter-app"
            }
        )
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        new_access_token = new_tokens["access_token"]
        
        # 4. Use new access token
        gateway_response2 = await client.get(
            "http://gateway:8000/api/v1/user/profile",
            headers={"Authorization": f"Bearer {new_access_token}"}
        )
        assert gateway_response2.status_code == 200
```

---

## 📊 Мониторинг интеграции

### Метрики для отслеживания

```python
from prometheus_client import Counter, Histogram

# JWT валидация
jwt_validation_total = Counter(
    "integration_jwt_validation_total",
    "Total JWT validations",
    ["service", "status"]
)

jwt_validation_duration = Histogram(
    "integration_jwt_validation_duration_seconds",
    "JWT validation duration",
    ["service"]
)

# JWKS кэш
jwks_cache_hits = Counter(
    "integration_jwks_cache_hits_total",
    "JWKS cache hits",
    ["service"]
)

jwks_cache_misses = Counter(
    "integration_jwks_cache_misses_total",
    "JWKS cache misses",
    ["service"]
)

# Ошибки интеграции
integration_errors = Counter(
    "integration_errors_total",
    "Integration errors",
    ["service", "error_type"]
)
```

### Логирование интеграции

```python
import logging

logger = logging.getLogger(__name__)

# Успешная валидация JWT
logger.info(
    "JWT validation successful",
    extra={
        "user_id": user_id,
        "client_id": client_id,
        "service": "gateway",
        "duration_ms": duration
    }
)

# Ошибка валидации
logger.error(
    "JWT validation failed",
    extra={
        "service": "gateway",
        "reason": "invalid_signature",
        "ip_address": ip
    }
)
```

---

## 🔄 Rollback план

### Если возникли проблемы с JWT аутентификацией:

1. **Анализ (1 час):**
   - Определить root cause
   - Обновить документацию
   - Предотвратить повторение

---

## ✅ Контрольный список интеграции

### Auth Service
- [ ] Развёрнут и работает
- [ ] JWKS endpoint доступен
- [ ] Тестовые пользователи созданы
- [ ] OAuth2 flow протестирован

### Codelab Core Service
- [ ] JWTAuthMiddleware добавлен
- [ ] Модели обновлены (user_id)
- [ ] Миграции применены
- [ ] Тесты проходят

### Мониторинг
- [ ] Метрики настроены
- [ ] Логирование работает
- [ ] Alerting настроен
- [ ] Dashboard создан

---

## 📞 Контакты

**Разработчик:** Sergey Penkovsky  
**Email:** sergey.penkovsky@gmail.com  
**Версия:** 1.0.0  
**Дата:** 2026-03-22
