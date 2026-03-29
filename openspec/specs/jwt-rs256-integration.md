# JWT RS256 интеграция и JWKS

**Версия:** 1.0.0  
**Статус:** ✅ Production Ready  
**Дата обновления:** 29 марта 2026

---

## 📋 Обзор

Auth Service генерирует JWT токены с использованием асимметричной криптографии RS256 (RSA + SHA-256). Это обеспечивает безопасную аутентификацию во всей микросервисной архитектуре CodeLab без необходимости делиться приватным ключом с другими сервисами.

**Ключевые преимущества RS256:**
- ✅ **Асимметричная криптография** — приватный ключ хранится только в auth-service
- ✅ **Масштабируемость** — другие сервисы могут валидировать токены публичным ключом
- ✅ **Без обмена секретами** — не нужно делиться secret между сервисами
- ✅ **Ротация ключей** — поддержка Key ID (kid) для смены ключей без перерыва

---

## 🔐 Архитектура RS256

### Асимметричная криптография

```
┌─────────────────────────────────────────────────────────────┐
│                    RSA Ключевая пара                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Приватный ключ (Private Key)                              │
│  ────────────────────────────                              │
│  - Хранится ТОЛЬКО в auth-service                          │
│  - Используется для ПОДПИСИ токенов                        │
│  - Длина: 2048 бит                                         │
│  - Формат: PEM-кодированный PKCS#8                         │
│                                                             │
│  Публичный ключ (Public Key)                               │
│  ───────────────────────────                               │
│  - Публикуется через JWKS endpoint                         │
│  - Используется для ПРОВЕРКИ подписи                       │
│  - Может быть распространен без ограничений                │
│  - Извлекается из приватного ключа                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Процесс подписи и верификации

```
ГЕНЕРАЦИЯ (в auth-service):
────────────────────────────
1. Создать payload с user data
2. Сериализовать в JSON
3. Подписать приватным ключом (RS256)
4. Закодировать в Base64URL
→ Получить JWT токен

ВАЛИДАЦИЯ (в других сервисах):
──────────────────────────────
1. Получить JWT из Authorization header
2. Распарсить header, payload, signature
3. Получить public key от auth-service (JWKS)
4. Проверить подпись public key
5. Валидировать claims (iss, aud, exp, и т.д.)
→ Если подпись корректна → токен валиден
```

---

## 🎫 Структура JWT токена

### JWT Format

JWT состоит из трёх частей, разделённых точками:

```
eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjIwMjQtMDEta2V5LTEifQ.
eyJpc3MiOiJodHRwczovL2F1dGguY29kZWxhYi5sb2NhbCIsInN1YiI6IjU1MGU4NDAwLWUyOWItNDFkNC1hNzE2LTQ0NjY1NTQ0MDAwMCIsImF1ZCI6ImNvZGVsYWItYXBpIiwiZXhwIjoxNzEwMDAwOTAwLCJpYXQiOjE3MTAwMDAwMDAsIm5iZiI6MTcxMDAwMDAwMCwic2NvcGUiOiJhcGk6cmVhZCBhcGk6d3JpdGUiLCJqdGkiOiJhMWIyYzNkNC1lNWY2LTc4OTAtYWJjZC1lZjEyMzQ1Njc4OTAiLCJ0eXBlIjoiYWNjZXNzIiwiY2xpZW50X2lkIjoiY29kZWxhYi1mbHV0dGVyLWFwcCJ9.
SIG_SIGNATURE_SIGNATURE_SIGNATURE...

│                                                    │
├─────── Header (Base64URL) ────────────────────────┤
│ Содержит метаинформацию о токене                 │
│                                                   │
├─────── Payload (Base64URL) ───────────────────────┤
│ Содержит claims (данные о пользователе)          │
│                                                   │
├─────── Signature (Base64URL) ─────────────────────┤
│ Криптографическая подпись                        │
│ (приватный ключ + хэш header + payload)          │
```

### 1. Header (Заголовок)

Содержит метаинформацию о типе токена и алгоритме подписи:

```json
{
  "alg": "RS256",      // Алгоритм подписи (RSA + SHA-256)
  "typ": "JWT",        // Тип токена
  "kid": "2024-01-key-1"  // Key ID для ротации ключей
}
```

**Параметры:**
- `alg` — всегда "RS256" (RSA 2048-bit + SHA-256)
- `typ` — всегда "JWT"
- `kid` — уникальный идентификатор ключа для ротации (формат: YYYY-MM-key-N)

### 2. Payload (Полезная нагрузка)

Содержит claims — утверждения о пользователе и его разрешениях:

#### Standard OIDC/OAuth2 Claims

| Claim | Тип | Описание | Пример |
|-------|-----|---------|--------|
| `iss` | string | Издатель токена (issuer) | `https://auth.codelab.local` |
| `sub` | string | Субъект токена = User ID (UUID) | `550e8400-e29b-41d4-a716-446655440000` |
| `aud` | string | Целевая аудитория (audience) | `codelab-api` |
| `exp` | integer | Время истечения (Unix timestamp) | `1710000900` |
| `iat` | integer | Время создания (Unix timestamp) | `1710000000` |
| `nbf` | integer | Не использовать ранее (not before) | `1710000000` |

#### Custom Claims

| Claim | Тип | Описание | Пример |
|-------|-----|---------|--------|
| `type` | string | Тип токена: `access` или `refresh` | `access` |
| `jti` | string | Уникальный ID токена (JWT ID, UUID) | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| `scope` | string | Разрешения (space-separated) | `api:read api:write` |
| `client_id` | string | ID клиента, запросивших токен | `codelab-flutter-app` |

#### Полный пример Payload'а (Access Token)

```json
{
  "iss": "https://auth.codelab.local",
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "aud": "codelab-api",
  "exp": 1710000900,
  "iat": 1710000000,
  "nbf": 1710000000,
  "jti": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "type": "access",
  "client_id": "codelab-flutter-app",
  "scope": "api:read api:write"
}
```

#### Полный пример Payload'а (Refresh Token)

```json
{
  "iss": "https://auth.codelab.local",
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "aud": "codelab-api",
  "exp": 1712592000,
  "iat": 1710000000,
  "nbf": 1710000000,
  "jti": "b2c3d4e5-f6a7-8901-bcde-f1234567890a",
  "type": "refresh",
  "client_id": "codelab-flutter-app",
  "scope": "api:read api:write"
}
```

### 3. Signature (Подпись)

Криптографическая подпись, созданная путем:

```python
signature = HMACSHA256(
  base64UrlEncode(header) + "." +
  base64UrlEncode(payload),
  private_key
)
```

Позволяет убедиться, что:
- Токен был создан auth-service (только текущий сервис имеет приватный ключ)
- Содержимое токена не было модифицировано

---

## 📤 Жизненные циклы токенов

### Access Token

- **Длительность:** 15 минут (900 секунд)
- **Назначение:** Доступ к защищённым ресурсам
- **Использование:** В заголовке `Authorization: Bearer <access_token>`
- **Валидация:** Все сервисы валидируют этот токен для каждого запроса

```javascript
// Пример вычисления exp для access token
const now = Math.floor(Date.now() / 1000);  // текущее время (Unix timestamp)
const access_exp = now + 900;                // + 15 минут
```

### Refresh Token

- **Длительность:** 30 дней (2592000 секунд)
- **Назначение:** Получение нового access token без переввода пароля
- **Использование:** POST /oauth/token с grant_type=refresh_token
- **Валидация:** Только auth-service валидирует этот токен

```javascript
// Пример вычисления exp для refresh token
const now = Math.floor(Date.now() / 1000);
const refresh_exp = now + (30 * 24 * 60 * 60);  // + 30 дней
```

### Timeline

```
┌─ Access Token создан
│  ├─ iat = 10:00:00
│  ├─ exp = 10:15:00  (15 минут)
│  └─ Используется в API запросах до 10:15:00
│
├─ Refresh Token создан
│  ├─ iat = 10:00:00
│  ├─ exp = 10:04:2026  (30 дней)
│  └─ Может использоваться до 10:04:2026
│
├─ Access Token истекает в 10:15:00
│  └─ Клиент получает "401 Unauthorized"
│
├─ Клиент отправляет refresh token в POST /oauth/token
│  └─ Получает новый access token
│
└─ Refresh token истекает в 10:04:2026
   └─ Клиент должен заново пройти аутентификацию
```

---

## 🔑 JWKS (JSON Web Key Set)

### Endpoint: GET /.well-known/jwks.json

Публичный endpoint для получения публичных ключей в стандартном формате JWKS (RFC 7517).

**URL:** `http://codelab-auth-service:8003/.well-known/jwks.json`

**Метод:** GET

**Аутентификация:** Не требуется (публичный endpoint)

**Headers:**
```http
GET /.well-known/jwks.json HTTP/1.1
Host: codelab-auth-service:8003
Accept: application/json
```

### Response Structure (200 OK)

```json
{
  "keys": [
    {
      "kty": "RSA",
      "use": "sig",
      "kid": "2024-01-key-1",
      "n": "xjlCRBKHfh5...base64url encoded modulus...",
      "e": "AQAB"
    },
    {
      "kty": "RSA",
      "use": "sig",
      "kid": "2024-01-key-2",
      "n": "yjmkDSDLGH6...base64url encoded modulus...",
      "e": "AQAB"
    }
  ]
}
```

**Поля каждого ключа:**

| Поле | Тип | Описание |
|------|-----|---------|
| `kty` | string | Тип ключа: всегда "RSA" |
| `use` | string | Использование: "sig" (подпись) |
| `kid` | string | Key ID: "YYYY-MM-key-N" |
| `alg` | string | Алгоритм: "RS256" |
| `n` | string | RSA модулус (Base64URL) |
| `e` | string | Публичный экспонент: "AQAB" (65537) |
| `x5c` | array | (опционально) X.509 сертификаты |

### Полный пример JWKS Response

```json
{
  "keys": [
    {
      "kty": "RSA",
      "use": "sig",
      "kid": "2024-01-key-1",
      "alg": "RS256",
      "n": "xjlCRBKHfh5nvBELlKXXM2S5GZ8w4-JKZH6kN8P5Q6R7S8T9U0V1W2X3Y4Z5A6B7C8D9E0F1G2H3I4J5K6L7M8N9O0P1Q2R3S4T5U6V7W8X9Y0Z1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7Q8R9S0T1U2V3W4X5Y6Z7A8B9C0D1E2F3G4H5I6J7K8L9M0N1O2P3Q4R5S6T7U8V9W0X1Y2Z3A4B5C6D7E8F9G0H1I2J3K4L5M6N7O8P9Q0R1S2T3U4V5W6X7Y8Z9A0B1C2D3E4F5G6H7I8J9K0L1M2N3O4P5Q6R7S8T9U0V1W2X3Y4Z5A6B7C8D9E0F1G2H3I4J5K6L7M8N9O0P1Q2R3S4T5U6V7W8X9Y0Z1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7Q8R9S0T1U2V3W4X5Y6Z7A8B9",
      "e": "AQAB"
    }
  ]
}
```

### Response Headers

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=3600
Content-Length: 1234
```

**Важные headers:**
- `Content-Type: application/json` — JSON формат
- `Cache-Control: public, max-age=3600` — Рекомендуется кэшировать на 1 час
- `Access-Control-Allow-Origin: *` — Доступ с других доменов

---

## 🔄 Ротация ключей (Key Rotation)

### Стратегия ротации

Auth Service поддерживает несколько ключей одновременно (обычно 1-2 текущих, старые в архиве):

**Жизненный цикл ключа:**

```
Шаг 1: Создание нового ключа
  - Генерируется новая RSA пара
  - Присваивается новый kid (например, "2024-02-key-2")
  - Добавляется в JWKS response

Шаг 2: Оба ключа работают параллельно
  - Новые токены подписываются новым ключом
  - Старые токены остаются валидны (используют старый kid)
  - JWKS содержит оба публичных ключа

Шаг 3: Вывод старого ключа из использования
  - Новые токены подписываются только новым ключом
  - Старый ключ остаётся в JWKS для валидации остающихся токенов
  - Клиенты кэшируют JWKS, поэтому нужно время для обновления

Шаг 4: Удаление старого ключа
  - После истечения всех оставшихся токенов
  - Старый ключ удаляется из JWKS (примерно через 30 дней)
```

### Пример ротации

```json
// JWKS до ротации (только старый ключ)
{
  "keys": [
    {
      "kid": "2024-01-key-1",
      "kty": "RSA",
      "n": "old_modulus_base64...",
      "e": "AQAB"
    }
  ]
}

↓ (Генерируется новый ключ)

// JWKS во время ротации (оба ключа)
{
  "keys": [
    {
      "kid": "2024-01-key-1",      // ← Старый (для валидации остающихся токенов)
      "kty": "RSA",
      "n": "old_modulus_base64...",
      "e": "AQAB"
    },
    {
      "kid": "2024-02-key-2",      // ← Новый (для подписи новых токенов)
      "kty": "RSA",
      "n": "new_modulus_base64...",
      "e": "AQAB"
    }
  ]
}

↓ (Прошло 30+ дней, все старые токены истекли)

// JWKS после ротации (только новый ключ)
{
  "keys": [
    {
      "kid": "2024-02-key-2",
      "kty": "RSA",
      "n": "new_modulus_base64...",
      "e": "AQAB"
    }
  ]
}
```

### Поддержка kid в токенах

Каждый токен содержит `kid` в заголовке для связи с правильным публичным ключом:

```python
# При создании токена
token = jwt.encode(
    payload,
    private_key,
    algorithm="RS256",
    headers={"kid": "2024-02-key-2"}  # ← Указываем kid
)

# При валидации
header = jwt.get_unverified_header(token)
kid = header["kid"]  # Получаем kid: "2024-02-key-2"

# Получаем правильный публичный ключ из JWKS
public_key = jwks_client.get_public_key(kid)

# Валидируем токен с этим ключом
jwt.decode(token, public_key, algorithms=["RS256"])
```

---

## 💻 Реализация в Code

### 1. TokenService — Создание токенов

**Файл:** [`app/services/token_service.py`](../../../codelab-auth-service/app/services/token_service.py)

```python
from jose import jwt
from app.core.security import rsa_key_manager

class TokenService:
    def __init__(self):
        self.algorithm = "RS256"

    def create_access_token(
        self,
        user_id: str,
        client_id: str,
        scope: str,
        lifetime: int | None = None,
    ) -> tuple[str, AccessTokenPayload]:
        """Создать access token"""
        if lifetime is None:
            lifetime = settings.access_token_lifetime
        
        now = datetime.now(timezone.utc)
        exp = now + timedelta(seconds=lifetime)
        
        payload = AccessTokenPayload(
            iss=settings.jwt_issuer,
            sub=user_id,                    # User ID (UUID)
            aud=settings.jwt_audience,
            exp=int(exp.timestamp()),
            iat=int(now.timestamp()),
            jti=str(uuid.uuid4()),
            type=TokenType.ACCESS,
            client_id=client_id,
            scope=scope,
        )
        
        # Подписываем приватным ключом
        token = jwt.encode(
            payload.model_dump(),
            rsa_key_manager.get_private_key_pem(),
            algorithm="RS256",
            headers={"kid": rsa_key_manager.kid}  # Key ID для ротации
        )
        
        return token, payload
```

### 2. JWKS Service — Публикация ключей

**Файл:** [`app/services/jwks_service.py`](../../../codelab-auth-service/app/services/jwks_service.py)

```python
class JWKSService:
    """Сервис для работы с JWKS"""
    
    @staticmethod
    def get_jwks_response() -> dict:
        """
        Получить JWKS в RFC 7517 формате
        
        Returns:
            JWKS response с публичными ключами
        """
        public_key = rsa_key_manager.get_public_key()
        
        jwk = {
            "kty": "RSA",
            "use": "sig",
            "kid": rsa_key_manager.kid,
            "alg": "RS256",
            "n": public_key.public_numbers().n,  # Модулус
            "e": public_key.public_numbers().e,  # Экспонент
        }
        
        return {
            "keys": [jwk]
        }
```

### 3. JWKS API Endpoint

**Файл:** [`app/api/v1/jwks.py`](../../../codelab-auth-service/app/api/v1/jwks.py)

```python
from fastapi import APIRouter, Response
from app.services.jwks_service import JWKSService

router = APIRouter()

@router.get("/.well-known/jwks.json")
async def get_jwks(response: Response) -> dict:
    """
    Получить JSON Web Key Set
    
    Возвращает публичные ключи в RFC 7517 формате
    для валидации JWT токенов.
    
    Returns:
        JWKS response с публичными ключами
    """
    # Кэширование на 1 час
    response.headers["Cache-Control"] = "public, max-age=3600"
    
    return JWKSService.get_jwks_response()
```

### 4. RSA Key Manager — Управление ключами

**Файл:** [`app/core/security.py`](../../../codelab-auth-service/app/core/security.py)

```python
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

class RSAKeyManager:
    """Менеджер для работы с RSA ключами"""
    
    def __init__(self):
        self.kid = "2024-01-key-1"  # Key ID для ротации
        self._private_key_pem = None
        self._public_key = None
        self._load_or_generate_keys()
    
    def _load_or_generate_keys(self):
        """Загрузить или сгенерировать RSA ключи"""
        # Пытаемся загрузить существующие ключи
        try:
            with open("keys/private_key.pem", "rb") as f:
                self._private_key_pem = f.read()
        except FileNotFoundError:
            # Генерируем новые ключи
            self._generate_keys()
    
    def _generate_keys(self):
        """Генерировать новую RSA пару (2048 бит)"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Сохраняем в PEM формате
        self._private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Сохраняем на диск
        with open("keys/private_key.pem", "wb") as f:
            f.write(self._private_key_pem)
    
    def get_private_key_pem(self) -> bytes:
        """Получить приватный ключ в PEM формате"""
        return self._private_key_pem
    
    def get_public_key(self):
        """Получить публичный ключ"""
        # Загружаем приватный ключ и извлекаем публичный
        from cryptography.hazmat.backends import default_backend
        
        private_key = serialization.load_pem_private_key(
            self._private_key_pem,
            password=None,
            backend=default_backend()
        )
        return private_key.public_key()

# Глобальный экземпляр
rsa_key_manager = RSAKeyManager()
```

---

## 🔍 Примеры использования

### Пример 1: Создание токенов (Python)

```python
from app.services.token_service import TokenService

service = TokenService()

# Создать пару токенов
token_pair = service.create_token_pair(
    user_id="550e8400-e29b-41d4-a716-446655440000",
    client_id="codelab-flutter-app",
    scope="api:read api:write",
)

access_token = token_pair.access_token
refresh_token = token_pair.refresh_token
```

### Пример 2: Получение JWKS (curl)

```bash
curl -H "Accept: application/json" \
  http://codelab-auth-service:8003/.well-known/jwks.json
```

### Пример 3: Валидация токена (Python)

```python
from jose import jwt

# Получить публичный ключ через JWKS
jwks_client = JWKSClient(
    jwks_url="http://codelab-auth-service:8003/.well-known/jwks.json"
)

token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjIwMjQtMDEta2V5LTEifQ..."

# Валидировать токен
try:
    payload = await jwks_client.validate_token(
        token,
        issuer="https://auth.codelab.local",
        audience="codelab-api"
    )
    user_id = payload["sub"]  # Получить user ID
except JWTError as e:
    # Токен невалиден
    return 401 Unauthorized
```

---

## ⚙️ Конфигурация

Управление JWT параметрами через переменные окружения:

```python
# app/core/config.py

# JWT Issuer и Audience
JWT_ISSUER: str = "https://auth.codelab.local"
JWT_AUDIENCE: str = "codelab-api"

# Lifetimes
ACCESS_TOKEN_LIFETIME: int = 900  # 15 минут в секундах
REFRESH_TOKEN_LIFETIME: int = 2592000  # 30 дней в секундах
```

Переменные окружения:

```bash
# .env
JWT_ISSUER=https://auth.codelab.local
JWT_AUDIENCE=codelab-api
ACCESS_TOKEN_LIFETIME=900
REFRESH_TOKEN_LIFETIME=2592000
```

---

## 📚 Ссылки

- [RFC 7519 — JSON Web Token (JWT)](https://tools.ietf.org/html/rfc7519)
- [RFC 7517 — JSON Web Key (JWK)](https://tools.ietf.org/html/rfc7517)
- [RFC 7518 — JSON Web Algorithms (JWA)](https://tools.ietf.org/html/rfc7518)
- [OIDC Core 1.0 — Claims](https://openid.net/specs/openid-connect-core-1_0.html#IDToken)

---

## 🔗 Интеграция с другими сервисами

Для валидации этих токенов в других сервисах, см:
- Core Service: [`jwt-validation/spec.md`](../../codelab-core-service/openspec/specs/jwt-validation/spec.md)
- Core Service: [`integration-with-auth-service/spec.md`](../../codelab-core-service/openspec/specs/integration-with-auth-service/spec.md)
