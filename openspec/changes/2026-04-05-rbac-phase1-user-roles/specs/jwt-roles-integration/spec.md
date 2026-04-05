# Specification: JWT Roles Integration

**Версия:** 1.0.0  
**Дата:** 5 апреля 2026  
**Статус:** Specification  

---

## 1. Overview

Данная спецификация описывает интеграцию roles в JWT токены, включая изменения в TokenService и валидацию в других микросервисах.

---

## 2. JWT Payload Structure

### 2.1 Phase 0 (Current — Scope-Based)

```json
{
  "iss": "https://auth.codelab.local",
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "scope": "api:read api:write",
  "client_id": "codelab-flutter-app",
  "iat": 1712300000,
  "exp": 1712303600
}
```

### 2.2 Phase 1 (After Implementation — Scope + Roles)

```json
{
  "iss": "https://auth.codelab.local",
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "scope": "api:read api:write",
  "roles": ["user", "moderator"],
  "client_id": "codelab-flutter-app",
  "iat": 1712300000,
  "exp": 1712303600
}
```

### 2.3 Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `iss` | string | Yes | Issuer (Auth Service URL) |
| `sub` | string | Yes | Subject (User ID) |
| `scope` | string | Yes | Space-separated scopes (backward compat) |
| `roles` | array[string] | Yes (Phase 1+) | List of role names assigned to user |
| `client_id` | string | Yes | OAuth2 client identifier |
| `iat` | integer | Yes | Issued at (Unix timestamp) |
| `exp` | integer | Yes | Expiration time (Unix timestamp) |

---

## 3. TokenService Changes

### 3.1 create_access_token() Method Signature

**Before (Phase 0):**
```python
async def create_access_token(
    self,
    db: AsyncSession,
    user_id: uuid.UUID,
    client_id: str,
    scope: str
) -> str:
    """Создать access token без ролей."""
    pass
```

**After (Phase 1):**
```python
async def create_access_token(
    self,
    db: AsyncSession,
    user_id: uuid.UUID,
    client_id: str,
    scope: str
) -> str:
    """Создать access token с ролями пользователя.
    
    Changes:
    - Получить роли пользователя из UserRoleService
    - Добавить roles в JWT payload
    - Гарантировать что в payload всегда есть scope и roles
    """
    pass
```

### 3.2 Implementation Details

```python
async def create_access_token(
    self,
    db: AsyncSession,
    user_id: uuid.UUID,
    client_id: str,
    scope: str
) -> str:
    """Создать access token с поддержкой ролей.
    
    Алгоритм:
    1. Получить пользователя из БД
    2. Получить роли пользователя (UserRoleService.get_user_roles)
    3. Гарантировать что есть default role "user" если список пуст
    4. Создать JWT payload с scope и roles
    5. Подписать JWT
    6. Вернуть token
    """
    # 1. Получить пользователя
    user = await self._get_user(db, user_id)
    if not user:
        raise UserNotFoundError(f"User '{user_id}' not found")
    
    # 2. Получить роли пользователя (используя selectinload для избежания N+1)
    user_role_service = UserRoleService()
    roles = await user_role_service.get_user_roles(db, user_id)
    
    # 3. Гарантировать что есть default role
    if not roles:
        roles = ["user"]
    elif "user" not in roles:
        roles.append("user")  # Все пользователи имеют минимум роль "user"
    
    # 4. Создать JWT payload
    now = datetime.utcnow()
    payload = {
        "iss": self.config.issuer,
        "sub": str(user_id),
        "scope": scope,
        "roles": roles,
        "client_id": client_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=self.config.access_token_expire)).timestamp())
    }
    
    # 5. Подписать JWT (RS256)
    token = jwt.encode(
        payload,
        self.config.private_key,
        algorithm="RS256"
    )
    
    # 6. Вернуть токен
    return token
```

### 3.3 Performance Considerations

**Query Optimization:**
- Использовать `selectinload(UserRoleMapping.role)` для eager loading
- One query для получения всех ролей (не N+1)
- Total time < 100ms даже для пользователя с 100+ ролей

```python
async def get_user_roles(
    self,
    db: AsyncSession,
    user_id: uuid.UUID
) -> list[str]:
    """Получить роли пользователя с оптимизацией."""
    result = await db.execute(
        select(UserRoleMapping).where(
            UserRoleMapping.user_id == user_id
        ).options(selectinload(UserRoleMapping.role))  # ← Eager loading!
    )
    mappings = result.scalars().all()
    return [mapping.role.name for mapping in mappings]
```

---

## 4. JWT Validation

### 4.1 JWKS Endpoint (Unchanged)

JWKS endpoint не меняется и остается на `/oauth/jwks`:

```http
GET /oauth/jwks HTTP/1.1
Host: auth.codelab.local

{
  "keys": [
    {
      "kty": "RSA",
      "use": "sig",
      "alg": "RS256",
      "n": "yGLlG7Z...",
      "e": "AQAB"
    }
  ]
}
```

### 4.2 Token Validation in Other Services

**Gateway (codelab-gateway):**
```python
# Получить публичный ключ из JWKS
jwks_client = JWKSClient(url="https://auth.codelab.local/oauth/jwks")
signing_key = jwks_client.get_signing_key_from_jwt(token)

# Валидировать JWT
payload = jwt.decode(
    token,
    signing_key.key,
    algorithms=["RS256"],
    issuer="https://auth.codelab.local"
)

# Использовать roles и scope из payload
user_roles = payload.get("roles", [])
user_scope = payload.get("scope", "")
```

### 4.3 Roles in Authorization Decisions

Другие микросервисы могут использовать roles для авторизации:

```python
async def authorize_user(request: Request):
    """Middleware для авторизации на основе ролей."""
    token = extract_token_from_header(request)
    payload = validate_and_decode_jwt(token)
    
    # Использовать роли для авторизации
    user_roles = payload.get("roles", [])
    
    # Пример: только admin может удалять проекты
    if request.method == "DELETE" and "admin" not in user_roles:
        raise ForbiddenError("Only admins can delete projects")
```

---

## 5. Backward Compatibility

### 5.1 Scope Field

- ✅ Поле `scope` сохраняется в JWT (не удаляется)
- ✅ Старые клиенты которые используют scope продолжают работать
- ✅ Новые клиенты могут использовать `roles` вместо/вместе со `scope`

### 5.2 Migration Path

**Phase 0 clients (using scope only):**
```json
{
  "scope": "api:read api:write"
  // Не используют roles
}
```

**Phase 1 clients (using roles):**
```json
{
  "scope": "api:read api:write",  // Still present
  "roles": ["user", "moderator"]   // New field
}
```

**Future clients (Phase 4+ using composite roles):**
```json
{
  "scope": "api:read api:write",
  "roles": ["user", "moderator"],
  "composite_roles": ["team-lead"]  // New in Phase 4
}
```

### 5.3 No Breaking Changes

- ❌ Нельзя удалять поле `scope` из JWT
- ❌ Нельзя менять формат существующих полей
- ✅ Только добавление нового поля `roles` (additive change)

---

## 6. Examples

### 6.1 JWT Example (Decoded)

```json
{
  "iss": "https://auth.codelab.local",
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "scope": "api:read api:write",
  "roles": [
    "user",
    "moderator"
  ],
  "client_id": "codelab-flutter-app",
  "iat": 1712300000,
  "exp": 1712303600
}
```

### 6.2 JWT Token (Encoded)

```
eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL2F1dGguY29kZWxhYi5sb2NhbCIsInN1YiI6IjU1MGU4NDAwLWUyOWItNDFkNC1hNzE2LTQ0NjY1NTQ0MDAwMCIsInNjb3BlIjoiYXBpOnJlYWQgYXBpOndyaXRlIiwicm9sZXMiOlsidXNlciIsIm1vZGVyYXRvciJdLCJjbGllbnRfaWQiOiJjb2RlbGFiLWZsdXR0ZXItYXBwIiwiaWF0IjoxNzEyMzAwMDAwLCJleHAiOjE3MTIzMDM2MDB9.signature_here
```

---

## 7. Error Handling

### 7.1 User Not Found

```python
async def create_access_token(...):
    user = await self._get_user(db, user_id)
    if not user:
        raise UserNotFoundError(f"User '{user_id}' not found")
    # Result: 404 Not Found
```

### 7.2 Database Error

```python
try:
    roles = await user_role_service.get_user_roles(db, user_id)
except Exception as e:
    logger.error(f"Failed to get user roles: {e}")
    raise TokenGenerationError("Internal server error")
    # Result: 500 Internal Server Error
```

---

## 8. Testing

### 8.1 Unit Tests

```python
@pytest.mark.asyncio
async def test_create_access_token_includes_roles(db):
    """JWT payload должен включать roles пользователя."""
    # Setup
    user = create_test_user()
    role = create_test_role("moderator")
    assign_role_to_user(user, role)
    
    # Execute
    token_service = TokenService()
    token = await token_service.create_access_token(
        db=db,
        user_id=user.id,
        client_id="test-client",
        scope="api:read"
    )
    
    # Verify
    payload = jwt.decode(token, key=public_key, algorithms=["RS256"])
    assert "roles" in payload
    assert "moderator" in payload["roles"]
    assert "user" in payload["roles"]  # Default role

@pytest.mark.asyncio
async def test_jwt_includes_scope_and_roles(db):
    """JWT должен включать и scope и roles (backward compatibility)."""
    # ...
    payload = jwt.decode(token, key=public_key, algorithms=["RS256"])
    assert payload["scope"] == "api:read api:write"
    assert isinstance(payload["roles"], list)
```

### 8.2 Integration Tests

```python
@pytest.mark.asyncio
async def test_token_validation_with_roles(db):
    """Другие сервисы должны валидировать JWT и использовать roles."""
    # Create token with roles
    token = await create_token_with_roles(db, roles=["user", "moderator"])
    
    # Gateway should be able to validate
    payload = validate_and_decode_jwt(token)
    assert payload["roles"] == ["user", "moderator"]
```

---

## 9. Migration Checklist

Before deploying Phase 1:
- [x] TokenService updated to include roles in JWT
- [x] All tests passing
- [x] JWKS endpoint still works (unchanged)
- [x] Backward compatibility verified (scope field present)
- [x] Performance tested (JWT creation < 100ms)
- [x] Documentation updated
- [x] Monitoring alerts configured

---

## 10. Acceptance Criteria

- [x] JWT payload contains roles field (array of strings)
- [x] Roles are correctly fetched from UserRoleService
- [x] Default role "user" is always present
- [x] Scope field is preserved (backward compatible)
- [x] JWT signature is valid (RS256)
- [x] JWKS endpoint works unchanged
- [x] All tests passing (unit + integration)
- [x] Performance < 100ms for token generation
- [x] Documentation complete

---

## References

- JWT Specification: https://tools.ietf.org/html/rfc7519
- OpenID Connect: https://openid.net/specs/openid-connect-core-1_0.html
- Design: [`../design.md`](../design.md)
- Phase 2: [`../../2026-04-12-rbac-phase2-role-mappers/`](../../2026-04-12-rbac-phase2-role-mappers/)
