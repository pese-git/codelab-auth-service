# RBAC Specification for CodeLab Auth Service

**Версия:** 2.0.0  
**Дата:** 05 апреля 2026  
**Статус:** 📋 Спецификация (перед реализацией)  
**Подход:** Hybrid (Keycloak-compatible на фазах 1-2, Groups-first на фазах 3+)

---

## 1. Overview

### 1.1 Цель документа

Настоящая спецификация описывает полную реализацию **Role-Based Access Control (RBAC)** для CodeLab Auth Service с постепенным расширением от простых пользовательских ролей к сложной системе групп, иерархии ролей и fine-grained авторизации.

### 1.2 Текущее состояние

- **Реализовано:** OAuth2 + JWT + scope-based авторизация (MVP)
- **Ограничения:** Нет поддержки ролей, групп, иерархии разрешений
- **JWT payload:** Содержит только `scope` (space-separated строка)

### 1.3 Целевое состояние (Post-MVP)

**Phase 1-2:**
- Пользовательские роли (User Roles)
- Role Mappers для JWT
- Предустановленные роли (admin, user, moderator)

**Phase 3-4:**
- Иерархические группы (Groups) с path-based структурой
- Composite Roles (иерархия ролей)
- Наследование разрешений

**Phase 5-6:**
- Admin UI для управления RBAC
- Fine-Grained Authorization (UMA 2.0 compatible)

### 1.4 Преимущества Hybrid Approach

| Аспект | Преимущество |
|--------|------------|
| Скорость старта | Phase 1-2 реализуются быстро (Keycloak-compatible) |
| Гибкость | Phase 3+ расширяют функциональность без переделки |
| Совместимость | Базовая совместимость с Keycloak на начальных фазах |
| Масштабируемость | Groups становятся основой организационной структуры |
| Миграция | Четкий путь к Keycloak если потребуется |

---

## 2. Architecture

### 2.1 Компоненты системы

```
┌─────────────────────────────────────────────────────────────┐
│                    Auth Service                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐      ┌──────────────────┐             │
│  │  User Management │      │  Role Management │             │
│  │                  │      │                  │             │
│  │ - Users          │      │ - User Roles     │             │
│  │ - Email/Password │      │ - Role Mappers   │             │
│  │ - Profiles       │      │ - Permissions    │             │
│  └──────────────────┘      └──────────────────┘             │
│           │                          │                      │
│           ▼                          ▼                      │
│  ┌──────────────────────────────────────────┐               │
│  │     Token Service (JWT Generation)       │               │
│  │                                          │               │
│  │  - Claims: sub, scope, roles, groups     │               │
│  │  - Role Mappers: apply at token time     │               │
│  │  - JWT Signing: RS256                    │               │
│  └──────────────────────────────────────────┘               │
│                     │                                       │
│  ┌──────────────────┐      ┌──────────────────┐             │
│  │  Group Management│      │  Permissions     │             │
│  │  (Phase 3+)      │      │  (Phase 4+)      │             │
│  │                  │      │                  │             │
│  │ - Groups         │      │ - Composite Roles│             │
│  │ - Hierarchies    │      │ - Role Hierarchy │             │
│  │ - Memberships    │      │ - Fine-Grained   │             │
│  └──────────────────┘      └──────────────────┘             │
│           │                          │                      │
│           └──────────────┬───────────┘                      │
│                          ▼                                  │
│               ┌──────────────────┐                          │
│               │   Audit Service  │                          │
│               │                  │                          │
│               │ - Role Changes   │                          │
│               │ - Permission Use │                          │
│               │ - Access Logs    │                          │
│               └──────────────────┘                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 JWT Payload эволюция

**Current (MVP — scope-based):**
```json
{
  "iss": "https://auth.codelab.local",
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "scope": "api:read api:write",
  "client_id": "codelab-flutter-app"
}
```

**Phase 1 (User Roles):**
```json
{
  "iss": "https://auth.codelab.local",
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "scope": "api:read api:write",
  "roles": ["user", "moderator"],
  "client_id": "codelab-flutter-app"
}
```

**Phase 2 (Role Mappers):**
```json
{
  "iss": "https://auth.codelab.local",
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "scope": "api:read api:write",
  "roles": ["user", "moderator"],
  "resource_access": {
    "codelab-flutter-app": {
      "roles": ["user", "content-viewer"]
    }
  },
  "client_id": "codelab-flutter-app"
}
```

**Phase 3 (Groups):**
```json
{
  "iss": "https://auth.codelab.local",
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "scope": "api:read api:write",
  "roles": ["user", "moderator"],
  "groups": ["/organization/acme-corp", "/organization/acme-corp/teams/engineering"],
  "resource_access": {
    "codelab-flutter-app": {
      "roles": ["user", "content-viewer"]
    }
  },
  "client_id": "codelab-flutter-app"
}
```

**Phase 4 (Composite Roles):**
```json
{
  "iss": "https://auth.codelab.local",
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "scope": "api:read api:write",
  "roles": ["user", "moderator"],
  "groups": ["/organization/acme-corp", "/organization/acme-corp/teams/engineering"],
  "composite_roles": ["team-lead", "content-manager"],
  "resource_access": {
    "codelab-flutter-app": {
      "roles": ["user", "content-viewer"]
    }
  },
  "client_id": "codelab-flutter-app"
}
```

### 2.3 Ключевые концепции

#### User Roles (Phase 1)
Глобальные роли пользователя, присваиваются напрямую пользователю.

```
User → Roles
john_doe → [user, moderator]
admin_user → [admin]
```

#### Role Mappers (Phase 2)
Правила преобразования ролей при создании JWT для конкретного клиента.

```
Client: codelab-flutter-app
Mapper: "user" → "codelab-flutter-app:content-viewer"
Mapper: "moderator" → "codelab-flutter-app:content-manager"

JWT resource_access.codelab-flutter-app.roles:
[user, moderator] → [content-viewer, content-manager]
```

#### Groups (Phase 3)
Иерархическая организационная структура с path-based идентификацией.

```
/organization/acme-corp
├── /organization/acme-corp/teams/engineering
│   └── /organization/acme-corp/teams/engineering/projects/backend
├── /organization/acme-corp/teams/sales
└── /organization/acme-corp/teams/management
```

#### Composite Roles (Phase 4)
Роли, составленные из других ролей, поддерживают иерархию.

```
Role: team-lead
  Includes: moderator, content-manager, report-viewer

JWT roles: [team-lead] →
Expanded roles: [moderator, content-manager, report-viewer, team-lead]
```

---

## 3. Data Models

### 3.1 Phase 1: User Roles

#### Таблица: `roles`

```sql
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT NULL,
    is_system_role BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT roles_name_length CHECK (char_length(name) >= 3)
);

CREATE INDEX idx_roles_name ON roles(name);
CREATE INDEX idx_roles_is_system_role ON roles(is_system_role);
```

**Поля:**
- `id`: UUID роли
- `name`: уникальное имя (например, "admin", "user", "moderator")
- `description`: описание роли
- `is_system_role`: встроенная роль (нельзя удалить)
- `created_at`, `updated_at`: временные метки

**Предустановленные роли:**
```sql
INSERT INTO roles (name, description, is_system_role) VALUES
  ('admin', 'Administrator with full access', true),
  ('user', 'Regular user with basic access', true),
  ('moderator', 'Moderator with content management', true);
```

---

#### Таблица: `user_role_mappings`

```sql
CREATE TABLE user_role_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT user_role_unique UNIQUE (user_id, role_id)
);

CREATE INDEX idx_user_role_mappings_user_id ON user_role_mappings(user_id);
CREATE INDEX idx_user_role_mappings_role_id ON user_role_mappings(role_id);
```

**Поля:**
- `id`: UUID записи
- `user_id`: ссылка на пользователя
- `role_id`: ссылка на роль
- `created_at`: дата назначения роли

---

### 3.2 Phase 2: Role Mappers

#### Таблица: `role_mappers`

```sql
CREATE TABLE role_mappers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id VARCHAR(255) NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    mapper_type VARCHAR(50) NOT NULL, -- 'role_to_role', 'hardcoded', 'conditional'
    config JSONB NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT role_mappers_unique UNIQUE (client_id, name)
);

CREATE INDEX idx_role_mappers_client_id ON role_mappers(client_id);
CREATE INDEX idx_role_mappers_mapper_type ON role_mappers(mapper_type);
CREATE INDEX idx_role_mappers_enabled ON role_mappers(enabled);
CREATE INDEX idx_role_mappers_priority ON role_mappers(priority);
```

**Поля:**
- `id`: UUID маппера
- `client_id`: клиент, к которому применяется маппер
- `name`: имя маппера (например, "user_to_viewer")
- `description`: описание
- `mapper_type`: тип маппера
  - `role_to_role`: преобразование одной роли в другую
  - `hardcoded`: добавление фиксированной роли
  - `conditional`: условное добавление на основе логики
- `config`: конфигурация (JSON зависит от типа)
- `enabled`: активен ли маппер
- `priority`: порядок применения (меньше = раньше)
- `created_at`, `updated_at`: временные метки

**Пример конфигурации role_to_role:**
```json
{
  "source_role": "user",
  "target_role": "codelab-flutter-app:content-viewer"
}
```

**Пример конфигурации hardcoded:**
```json
{
  "role": "codelab-flutter-app:default-user"
}
```

**Пример конфигурации conditional:**
```json
{
  "condition": "user.is_verified == true",
  "role": "codelab-flutter-app:verified-user"
}
```

---

### 3.3 Phase 3: Groups

#### Таблица: `groups`

```sql
CREATE TABLE groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    path VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    parent_id UUID NULL REFERENCES groups(id) ON DELETE CASCADE,
    description TEXT NULL,
    is_system_group BOOLEAN DEFAULT FALSE,
    attributes JSONB NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT groups_path_format CHECK (path ~ '^/[a-z0-9_/-]+$'),
    CONSTRAINT groups_name_length CHECK (char_length(name) >= 1)
);

CREATE INDEX idx_groups_path ON groups(path);
CREATE INDEX idx_groups_parent_id ON groups(parent_id);
CREATE INDEX idx_groups_name ON groups(name);
```

**Поля:**
- `id`: UUID группы
- `path`: иерархический путь (например, `/organization/acme-corp/teams/engineering`)
- `name`: отображаемое имя группы
- `parent_id`: ссылка на родительскую группу
- `description`: описание
- `is_system_group`: встроенная группа
- `attributes`: доп. атрибуты (JSON)
- `created_at`, `updated_at`: временные метки

**Примеры путей:**
```
/organization/acme-corp
/organization/acme-corp/teams/engineering
/organization/acme-corp/teams/engineering/projects/backend
/department/sales
/department/sales/regions/europe
```

---

#### Таблица: `user_group_memberships`

```sql
CREATE TABLE user_group_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    role_in_group VARCHAR(100) NULL, -- опционально: роль в группе
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT user_group_unique UNIQUE (user_id, group_id)
);

CREATE INDEX idx_user_group_memberships_user_id ON user_group_memberships(user_id);
CREATE INDEX idx_user_group_memberships_group_id ON user_group_memberships(group_id);
```

**Поля:**
- `id`: UUID записи
- `user_id`: ссылка на пользователя
- `group_id`: ссылка на группу
- `role_in_group`: опционально, роль в контексте группы (например, "group-admin")
- `created_at`: дата вступления в группу

---

#### Таблица: `group_role_mappings`

```sql
CREATE TABLE group_role_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT group_role_unique UNIQUE (group_id, role_id)
);

CREATE INDEX idx_group_role_mappings_group_id ON group_role_mappings(group_id);
CREATE INDEX idx_group_role_mappings_role_id ON group_role_mappings(role_id);
```

**Поля:**
- `id`: UUID записи
- `group_id`: ссылка на группу
- `role_id`: ссылка на роль
- `created_at`: дата назначения

**Логика наследования:**
```
Пользователь член группы → получает все роли группы
User member of /org/acme/teams/eng → получает все роли группы
```

---

### 3.4 Phase 4: Composite Roles

#### Таблица: `composite_role_mappings`

```sql
CREATE TABLE composite_role_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    child_role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT composite_role_unique UNIQUE (parent_role_id, child_role_id),
    CONSTRAINT not_self_reference CHECK (parent_role_id != child_role_id)
);

CREATE INDEX idx_composite_role_mappings_parent ON composite_role_mappings(parent_role_id);
CREATE INDEX idx_composite_role_mappings_child ON composite_role_mappings(child_role_id);
```

**Поля:**
- `id`: UUID записи
- `parent_role_id`: роль, которая содержит другие роли
- `child_role_id`: роль, которая входит в parent_role
- `created_at`: дата создания связи

**Пример иерархии:**
```
Role: team-lead
├─ moderator
├─ content-manager
└─ report-viewer

Role: moderator
├─ content-editor
└─ comment-manager
```

---

### 3.5 Phase 5-6: Permissions и Fine-Grained Authorization

#### Таблица: `permissions`

```sql
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_id VARCHAR(255) NOT NULL,
    action VARCHAR(100) NOT NULL,
    description TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT permissions_unique UNIQUE (resource_id, action)
);

CREATE INDEX idx_permissions_resource_id ON permissions(resource_id);
CREATE INDEX idx_permissions_action ON permissions(action);
```

**Поля:**
- `id`: UUID разрешения
- `resource_id`: тип ресурса (например, "project", "agent", "workspace")
- `action`: действие (например, "read", "write", "delete")
- `description`: описание
- `created_at`: дата создания

**Примеры:**
```
project:read, project:write, project:delete
agent:execute, agent:manage, agent:view
workspace:create, workspace:admin
```

---

#### Таблица: `role_permission_mappings`

```sql
CREATE TABLE role_permission_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT role_permission_unique UNIQUE (role_id, permission_id)
);

CREATE INDEX idx_role_permission_mappings_role_id ON role_permission_mappings(role_id);
CREATE INDEX idx_role_permission_mappings_permission_id ON role_permission_mappings(permission_id);
```

---

## 4. JWT Structure Updates

### 4.1 Current JWT Payload (MVP)

```json
{
  "iss": "https://auth.codelab.local",
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "aud": "codelab-api",
  "exp": 1710000900,
  "iat": 1710000000,
  "nbf": 1710000000,
  "scope": "api:read api:write",
  "jti": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "type": "access",
  "client_id": "codelab-flutter-app"
}
```

### 4.2 Phase 1: User Roles in JWT

```json
{
  "iss": "https://auth.codelab.local",
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "aud": "codelab-api",
  "exp": 1710000900,
  "iat": 1710000000,
  "nbf": 1710000000,
  "scope": "api:read api:write",
  "roles": ["user", "moderator"],
  "jti": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "type": "access",
  "client_id": "codelab-flutter-app"
}
```

### 4.3 Phase 2-3: Role Mappers & Groups

```json
{
  "iss": "https://auth.codelab.local",
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "aud": "codelab-api",
  "exp": 1710000900,
  "iat": 1710000000,
  "nbf": 1710000000,
  "scope": "api:read api:write",
  "roles": ["user", "moderator"],
  "groups": ["/organization/acme-corp", "/organization/acme-corp/teams/engineering"],
  "resource_access": {
    "codelab-flutter-app": {
      "roles": ["content-viewer", "content-manager"]
    },
    "codelab-core-service": {
      "roles": ["agent-viewer"]
    }
  },
  "jti": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "type": "access",
  "client_id": "codelab-flutter-app"
}
```

### 4.4 Phase 4: Composite Roles (Expanded)

```json
{
  "iss": "https://auth.codelab.local",
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "aud": "codelab-api",
  "exp": 1710000900,
  "iat": 1710000000,
  "nbf": 1710000000,
  "scope": "api:read api:write",
  "roles": ["user", "moderator", "team-lead"],
  "expanded_roles": ["user", "moderator", "team-lead", "content-manager", "report-viewer"],
  "groups": ["/organization/acme-corp", "/organization/acme-corp/teams/engineering"],
  "resource_access": {
    "codelab-flutter-app": {
      "roles": ["content-viewer", "content-manager"]
    },
    "codelab-core-service": {
      "roles": ["agent-viewer", "agent-executor"]
    }
  },
  "jti": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "type": "access",
  "client_id": "codelab-flutter-app"
}
```

### 4.5 JWT Generation Algorithm

```python
def generate_access_token(user_id: str, client_id: str) -> str:
    """Generate JWT with RBAC claims"""
    
    # 1. Получить пользователя
    user = get_user(user_id)
    
    # 2. Получить пользовательские роли (Phase 1)
    user_roles = get_user_roles(user_id)
    
    # 3. Получить роли из групп (Phase 3)
    group_roles = get_roles_from_user_groups(user_id)
    all_roles = set(user_roles + group_roles)
    
    # 4. Разворачивание composite roles (Phase 4)
    expanded_roles = expand_composite_roles(all_roles)
    
    # 5. Применить role mappers (Phase 2)
    client = get_oauth_client(client_id)
    mapped_roles = apply_role_mappers(all_roles, client)
    
    # 6. Получить scope (backward compatibility)
    scope = client.allowed_scopes
    
    # 7. Построить JWT payload
    payload = {
        "iss": config.JWT_ISSUER,
        "sub": user_id,
        "aud": config.JWT_AUDIENCE,
        "exp": int(time.time()) + client.access_token_lifetime,
        "iat": int(time.time()),
        "scope": scope,
        "roles": list(all_roles),
        "expanded_roles": list(expanded_roles),  # Phase 4
        "groups": get_user_group_paths(user_id),  # Phase 3
        "resource_access": {
            resource_id: {"roles": roles}
            for resource_id, roles in mapped_roles.items()
        },  # Phase 2
        "jti": str(uuid.uuid4()),
        "type": "access",
        "client_id": client_id
    }
    
    # 8. Подписать JWT
    return encode_jwt(payload, config.PRIVATE_KEY)
```

---

## 5. API Endpoints

### 5.1 Role Management APIs (Phase 1)

#### POST /api/v1/admin/roles

**Назначение:** Создание новой роли

**Требует:** Bearer token с ролью `admin`

**Запрос:**
```http
POST /api/v1/admin/roles HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "content-manager",
  "description": "Can manage content"
}
```

**Ответ (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "content-manager",
  "description": "Can manage content",
  "is_system_role": false,
  "created_at": "2026-04-05T10:00:00Z"
}
```

---

#### GET /api/v1/admin/roles

**Назначение:** Список всех ролей

**Параметры:**
- `skip` (query, optional): пропустить (default: 0)
- `limit` (query, optional): лимит (default: 50)
- `search` (query, optional): поиск по имени

**Ответ (200 OK):**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "admin",
      "description": "Administrator",
      "is_system_role": true
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "user",
      "description": "Regular user",
      "is_system_role": true
    }
  ],
  "total": 2
}
```

---

#### POST /api/v1/admin/users/{user_id}/roles

**Назначение:** Назначить роль пользователю

**Запрос:**
```http
POST /api/v1/admin/users/550e8400-e29b-41d4-a716-446655440000/roles HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "role_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

**Ответ (201 Created):**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "role_id": "550e8400-e29b-41d4-a716-446655440001",
  "created_at": "2026-04-05T10:00:00Z"
}
```

---

#### GET /api/v1/admin/users/{user_id}/roles

**Назначение:** Список ролей пользователя

**Ответ (200 OK):**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "roles": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "user",
      "description": "Regular user"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "name": "moderator",
      "description": "Content moderator"
    }
  ]
}
```

---

#### DELETE /api/v1/admin/users/{user_id}/roles/{role_id}

**Назначение:** Удалить роль пользователя

**Ответ (204 No Content)**

---

### 5.2 Role Mapper APIs (Phase 2)

#### POST /api/v1/admin/clients/{client_id}/role-mappers

**Назначение:** Создать role mapper

**Запрос:**
```http
POST /api/v1/admin/clients/codelab-flutter-app/role-mappers HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "user-to-viewer",
  "description": "Map user role to content-viewer",
  "mapper_type": "role_to_role",
  "config": {
    "source_role": "user",
    "target_role": "codelab-flutter-app:content-viewer"
  },
  "enabled": true,
  "priority": 0
}
```

**Ответ (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440010",
  "client_id": "codelab-flutter-app",
  "name": "user-to-viewer",
  "mapper_type": "role_to_role",
  "config": {
    "source_role": "user",
    "target_role": "codelab-flutter-app:content-viewer"
  },
  "enabled": true,
  "priority": 0,
  "created_at": "2026-04-05T10:00:00Z"
}
```

---

#### GET /api/v1/admin/clients/{client_id}/role-mappers

**Назначение:** Список role mappers для клиента

**Ответ (200 OK):**
```json
{
  "client_id": "codelab-flutter-app",
  "mappers": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440010",
      "name": "user-to-viewer",
      "mapper_type": "role_to_role",
      "enabled": true,
      "priority": 0
    }
  ]
}
```

---

### 5.3 Group APIs (Phase 3)

#### POST /api/v1/admin/groups

**Назначение:** Создать группу

**Запрос:**
```http
POST /api/v1/admin/groups HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "path": "/organization/acme-corp",
  "name": "Acme Corporation",
  "description": "Main organization"
}
```

**Ответ (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440020",
  "path": "/organization/acme-corp",
  "name": "Acme Corporation",
  "parent_id": null,
  "created_at": "2026-04-05T10:00:00Z"
}
```

---

#### POST /api/v1/admin/groups/{group_id}/members

**Назначение:** Добавить пользователя в группу

**Запрос:**
```http
POST /api/v1/admin/groups/550e8400-e29b-41d4-a716-446655440020/members HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "role_in_group": "group-admin"
}
```

**Ответ (201 Created):**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "group_id": "550e8400-e29b-41d4-a716-446655440020",
  "role_in_group": "group-admin",
  "created_at": "2026-04-05T10:00:00Z"
}
```

---

#### POST /api/v1/admin/groups/{group_id}/roles

**Назначение:** Назначить роль группе

**Запрос:**
```http
POST /api/v1/admin/groups/550e8400-e29b-41d4-a716-446655440020/roles HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "role_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

**Ответ (201 Created):**
```json
{
  "group_id": "550e8400-e29b-41d4-a716-446655440020",
  "role_id": "550e8400-e29b-41d4-a716-446655440001",
  "created_at": "2026-04-05T10:00:00Z"
}
```

---

### 5.4 Composite Role APIs (Phase 4)

#### POST /api/v1/admin/roles/{role_id}/composite-roles

**Назначение:** Добавить role в composite role

**Запрос:**
```http
POST /api/v1/admin/roles/550e8400-e29b-41d4-a716-446655440030/composite-roles HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "child_role_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

**Ответ (201 Created):**
```json
{
  "parent_role_id": "550e8400-e29b-41d4-a716-446655440030",
  "child_role_id": "550e8400-e29b-41d4-a716-446655440001",
  "created_at": "2026-04-05T10:00:00Z"
}
```

---

### 5.5 Authorization Check APIs

#### POST /api/v1/auth/check-permission

**Назначение:** Проверить есть ли у пользователя разрешение (используется сервисами)

**Запрос:**
```http
POST /api/v1/auth/check-permission HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "resource_id": "project",
  "action": "write"
}
```

**Ответ (200 OK):**
```json
{
  "has_permission": true,
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "resource_id": "project",
  "action": "write"
}
```

---

#### POST /api/v1/auth/check-role

**Назначение:** Проверить есть ли у пользователя роль

**Запрос:**
```http
POST /api/v1/auth/check-role HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "role": "admin"
}
```

**Ответ (200 OK):**
```json
{
  "has_role": true,
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "admin"
}
```

---

## 6. Implementation Phases

### 6.1 Phase 1: User Roles (Критично)

**Цель:** Добавить базовую поддержку пользовательских ролей в JWT

**Сроки:** 2-3 недели  
**Приоритет:** 🔴 CRITICAL  
**Блокирует:** Phases 2-6

**Deliverables:**

- ✅ Таблицы БД: `roles`, `user_role_mappings`
- ✅ Модели SQLAlchemy
- ✅ Миграция Alembic
- ✅ API endpoints для управления ролями (CRUD)
- ✅ JWT generation с полем `roles`
- ✅ Тесты (unit + integration)
- ✅ Документация

**Acceptance Criteria:**

- [ ] Пользователь может получить роли через JWT
- [ ] Admin может назначить/удалить роли пользователю
- [ ] JWT содержит массив `roles`
- [ ] Тесты покрывают все основные сценарии (coverage > 80%)
- [ ] Документация API актуальна

**Risks:**

- ⚠️ Обратная совместимость с текущей scope-based авторизацией
- ⚠️ Performance при получении ролей (нужны индексы)

**Mitigation:**

- ✅ Добавляем `roles` в JWT параллельно с `scope`
- ✅ Кэширование ролей в Redis (TTL 5 минут)

---

### 6.2 Phase 2: Role Mappers (Важно)

**Цель:** Реализовать role mappers для преобразования ролей при создании JWT

**Сроки:** 2-3 недели  
**Приоритет:** 🟡 HIGH  
**Блокирует:** Phases 3-6

**Deliverables:**

- ✅ Таблица БД: `role_mappers`
- ✅ Модель SQLAlchemy
- ✅ Миграция Alembic
- ✅ API endpoints для управления mappers (CRUD)
- ✅ Логика применения mappers при JWT generation
- ✅ Поддержка типов mappers:
  - `role_to_role`: преобразование ролей
  - `hardcoded`: добавление фиксированной роли
  - `conditional`: условное добавление
- ✅ JWT payload с `resource_access`
- ✅ Тесты и документация

**Acceptance Criteria:**

- [ ] Role mappers применяются при создании JWT
- [ ] JWT содержит `resource_access` с mapped ролями
- [ ] Поддержаны все типы mappers
- [ ] Priority и enabled работают корректно
- [ ] Тесты coverage > 80%

**Risks:**

- ⚠️ Сложная логика применения mappers
- ⚠️ Performance при большом количестве mappers

**Mitigation:**

- ✅ Кэширование mappers в Redis
- ✅ Оптимизация запросов (предварительная загрузка)

---

### 6.3 Phase 3: Groups (Важно)

**Цель:** Реализовать иерархические группы с path-based идентификацией

**Сроки:** 3-4 недели  
**Приоритет:** 🟡 HIGH  
**Блокирует:** Phases 4-6

**Deliverables:**

- ✅ Таблицы БД: `groups`, `user_group_memberships`, `group_role_mappings`
- ✅ Модели SQLAlchemy
- ✅ Миграции Alembic
- ✅ API endpoints:
  - Управление группами (CRUD)
  - Добавление/удаление членов
  - Управление ролями групп
  - Получение иерархии групп
- ✅ Логика наследования ролей от групп
- ✅ JWT payload с полем `groups`
- ✅ Тесты и документация

**Acceptance Criteria:**

- [ ] Groups хранятся в БД с иерархией
- [ ] Path-based идентификация работает
- [ ] Пользователи могут быть членами групп
- [ ] JWT содержит список групп пользователя
- [ ] Роли групп наследуются пользователями
- [ ] Иерархия групп поддерживается (parent_id)
- [ ] Тесты coverage > 80%

**Risks:**

- ⚠️ Циклические ссылки в иерархии
- ⚠️ Performance при глубокой иерархии
- ⚠️ Сложность логики наследования ролей

**Mitigation:**

- ✅ Валидация при создании групп (check_circular_reference)
- ✅ Кэширование иерархии в Redis
- ✅ Ограничение глубины иерархии

---

### 6.4 Phase 4: Composite Roles (Важно)

**Цель:** Поддержка иерархии ролей (роли могут содержать другие роли)

**Сроки:** 2-3 недели  
**Приоритет:** 🟡 HIGH  
**Блокирует:** Phase 5-6

**Deliverables:**

- ✅ Таблица БД: `composite_role_mappings`
- ✅ Модель SQLAlchemy
- ✅ Миграция Alembic
- ✅ API endpoints для управления composite ролями
- ✅ Алгоритм разворачивания composite roles (recursive expansion)
- ✅ JWT payload с полем `expanded_roles`
- ✅ Тесты и документация

**Acceptance Criteria:**

- [ ] Composite roles поддерживаются
- [ ] Циклические ссылки обнаруживаются и предотвращаются
- [ ] JWT содержит как `roles` так и `expanded_roles`
- [ ] Разворачивание работает на любой глубине
- [ ] Performance optimized (кэширование)
- [ ] Тесты coverage > 80%

**Risks:**

- ⚠️ Циклические ссылки в иерархии ролей
- ⚠️ Performance при разворачивании глубоких иерархий
- ⚠️ JWT payload может быть большим

**Mitigation:**

- ✅ Валидация при создании (detect cycles)
- ✅ Кэширование expanded roles
- ✅ Ограничение размера JWT (если нужно)

---

### 6.5 Phase 5: Admin UI (Важно)

**Цель:** Интеграция управления RBAC с codelab-admin-frontend

**Сроки:** 4-5 недель  
**Приоритет:** 🟡 HIGH  
**Зависит от:** Phases 1-4

**Deliverables:**

- ✅ UI компоненты для управления:
  - Ролями
  - Role Mappers
  - Группами
  - Composite ролями
  - Разрешениями
- ✅ Страницы:
  - `/admin/roles` — список и управление ролями
  - `/admin/users/{id}/roles` — назначение ролей пользователю
  - `/admin/groups` — управление группами
  - `/admin/mappers` — управление role mappers
- ✅ API интеграция с auth-service
- ✅ Авторизация (только admin может управлять)
- ✅ Тесты и документация

**Acceptance Criteria:**

- [ ] Все основные операции доступны через UI
- [ ] Авторизация работает (только admin)
- [ ] UX интуитивный и удобный
- [ ] Mobile responsive
- [ ] Производительность приемлема

---

### 6.6 Phase 6: Fine-Grained Authorization (Опционально)

**Цель:** UMA 2.0 compatible fine-grained authorization система

**Сроки:** 6-8 недель  
**Приоритет:** 🟢 LOW  
**Зависит от:** Phases 1-5

**Deliverables:**

- ✅ Таблицы БД для permissions и policies
- ✅ Authorization engine
- ✅ API endpoints для управления ресурсами и политиками
- ✅ Decision engine для проверки доступа
- ✅ UMA 2.0 compatible endpoints
- ✅ Тесты и документация

**Acceptance Criteria:**

- [ ] Fine-grained permissions поддерживаются
- [ ] Policies применяются корректно
- [ ] UMA 2.0 compatible
- [ ] Performance приемлема

---

## 7. Migration Strategy

### 7.1 Фазы миграции

#### Фаза 1: Параллельная работа (1-2 недели)

**Состояние:** MVP Phase 1-2 реализованы (User Roles + Role Mappers)

```
Текущее состояние:
├─ Scope-based авторизация работает
├─ JWT содержит только "scope"
└─ Все клиенты используют scope

Новое состояние:
├─ JWT содержит и "scope" и "roles"
├─ Клиенты могут использовать оба подхода
├─ Роли не требуются для работы (backward compatible)
└─ Admin может начать назначать роли
```

**Изменения в JWT:**
```json
// До (MVP)
{
  "scope": "api:read api:write"
}

// После (Phase 1-2, backward compatible)
{
  "scope": "api:read api:write",
  "roles": ["user"],
  "resource_access": {}
}
```

**Клиенты:**
- ✅ Старые клиенты продолжают работать (используют `scope`)
- ✅ Новые клиенты могут использовать `roles`
- ✅ Нет обязательного обновления клиентов

---

#### Фаза 2: Постепенный переход (2-4 недели)

**Состояние:** Phase 3 (Groups) реализована и протестирована

```
Новое состояние:
├─ Groups внедрены и используются
├─ Пользователи распределены по группам
├─ JWT содержит "groups" и "roles"
├─ Role mappers учитывают группы
└─ Старая scope-based авторизация все еще работает
```

**Миграционные шаги:**
1. Создать группы в БД, отражающие текущую организационную структуру
2. Постепенно добавлять пользователей в группы
3. Назначать роли группам (вместо прямого назначения ролей пользователям)
4. Тестировать JWT с groups
5. Обновить документацию

---

#### Фаза 3: Полный переход (4-6 недель)

**Состояние:** Phase 4-5 полностью реализованы (Composite Roles + Admin UI)

```
Новое состояние:
├─ Groups — основа организационной структуры
├─ Composite roles — основа иерархии разрешений
├─ Admin UI — основной инструмент управления
├─ Role mappers — автоматическое преобразование
└─ Scope-based авторизация deprecated (но все еще работает)
```

**Что удалить:**
- ❌ Прямое назначение ролей пользователям (все через группы)
- ❌ Scope-based авторизация (заменена role-based)
- ❌ Старые документы и примеры

---

### 7.2 Backward Compatibility

#### JWT Compatibility

```python
# Оба поля присутствуют в JWT для полной backward compatibility
{
    "scope": "api:read api:write",    # MVP (старое, может быть deprecated)
    "roles": ["user", "moderator"],   # Phase 1+ (новое, required)
    "groups": ["/org/acme"],          # Phase 3+ (новое, опционально)
    "resource_access": {...}          # Phase 2+ (новое, опционально)
}
```

#### API Compatibility

**Старые endpoints остаются работающими:**
- ✅ `POST /oauth/token` — работает без изменений
- ✅ `GET /.well-known/jwks.json` — работает без изменений
- ✅ `POST /oauth/revoke` — работает без изменений

**Новые endpoints добавляются параллельно:**
- ✅ `/api/v1/admin/roles/*` — новые endpoints Phase 1
- ✅ `/api/v1/admin/*/role-mappers` — новые endpoints Phase 2
- ✅ `/api/v1/admin/groups/*` — новые endpoints Phase 3

---

### 7.3 Data Migration Plan

#### Миграция существующих данных

```sql
-- Phase 1: Создать роль "user" для всех существующих пользователей
INSERT INTO user_role_mappings (user_id, role_id)
SELECT id, (SELECT id FROM roles WHERE name = 'user')
FROM users
WHERE id NOT IN (SELECT user_id FROM user_role_mappings);

-- Phase 3: Создать организационные группы
INSERT INTO groups (path, name)
VALUES ('/default-organization', 'Default Organization');

-- Добавить всех пользователей в default organization
INSERT INTO user_group_memberships (user_id, group_id)
SELECT u.id, g.id
FROM users u, groups g
WHERE g.path = '/default-organization'
  AND u.id NOT IN (SELECT user_id FROM user_group_memberships);
```

---

### 7.4 Testing Strategy

#### Unit Tests

- ✅ Модели (roles, groups, mappers)
- ✅ Сервисы (role service, group service)
- ✅ JWT generation с разными ролями
- ✅ Role mapper application
- ✅ Composite role expansion

#### Integration Tests

- ✅ Полный OAuth2 flow с ролями
- ✅ JWT содержит правильные роли
- ✅ Role mapper применяется корректно
- ✅ Group inheritance работает
- ✅ Backward compatibility с scope-based

#### End-to-End Tests

- ✅ Admin создает роль и назначает пользователю
- ✅ Пользователь получает токен с ролью
- ✅ Resource server проверяет роль из JWT
- ✅ Group membership влияет на токен

---

## 8. Security Considerations

### 8.1 Принципы безопасности

#### Least Privilege
- ✅ Пользователи получают минимально необходимые роли
- ✅ Роли назначаются явно (нет defaults)
- ✅ Регулярный аудит разрешений

#### Separation of Concerns
- ✅ Роль != разрешение
- ✅ Разрешения определяют what (читать/писать)
- ✅ Роли определяют who (пользователь/админ)
- ✅ Группы определяют where (организация/отдел)

#### Audit Trail
- ✅ Все изменения ролей логируются
- ✅ История кто, что, когда изменил
- ✅ Retention policy для аудит логов (90 дней)

---

### 8.2 Защита от атак

#### Role Elevation
```
❌ Плохо: Пользователь может себе назначить admin роль
✅ Хорошо: Только админ может назначать роли через API
```

**Mitigation:**
- ✅ Все endpoints требуют Bearer token с ролью `admin`
- ✅ Rate limiting на endpoints управления ролями
- ✅ Аудит всех попыток изменения ролей

#### Role Injection
```
❌ Плохо: Клиент может добавить роль в JWT
✅ Хорошо: Роли генерируются на сервере, JWT подписан
```

**Mitigation:**
- ✅ JWT подписан RS256 (асимметричная криптография)
- ✅ Клиент не имеет приватного ключа
- ✅ Любое изменение JWT будет обнаружено

#### Privilege Escalation
```
❌ Плохо: Role mapper может добавить admin роль к обычному пользователю
✅ Хорошо: Mappers настраиваются админом, логируются все изменения
```

**Mitigation:**
- ✅ Role mappers создаются/удаляются только админом
- ✅ Priority порядок контролирует применение
- ✅ Аудит всех изменений mappers

---

### 8.3 JWT Security

#### Token Claims Validation
```python
# Проверка при создании token
assert user_id is not None  # Sub не может быть пустым
assert len(roles) <= MAX_ROLES  # Защита от JWT bloat
assert all(is_valid_role_name(r) for r in roles)  # Валидация ролей
```

#### Token Size Management
```
⚠️ Problem: JWT может стать очень большим с много ролями
Solution:
- Ограничить количество ролей в JWT (max 50)
- Использовать reference instead of full list для больших наборов
- Кэшировать expanded roles на клиентской стороне
```

---

## 9. Performance Considerations

### 9.1 Database Optimization

#### Индексы

```sql
-- Phase 1
CREATE INDEX idx_user_role_mappings_user_id ON user_role_mappings(user_id);
CREATE INDEX idx_user_role_mappings_role_id ON user_role_mappings(role_id);

-- Phase 3
CREATE INDEX idx_user_group_memberships_user_id ON user_group_memberships(user_id);
CREATE INDEX idx_group_role_mappings_group_id ON group_role_mappings(group_id);

-- Phase 4
CREATE INDEX idx_composite_role_mappings_parent ON composite_role_mappings(parent_role_id);
```

#### Query Optimization

```python
# Плохо: N+1 queries
for user_id in user_ids:
    roles = db.query(Role).join(UserRoleMapping).filter(UserRoleMapping.user_id == user_id)
    # N+1 queries!

# Хорошо: Single query с join
roles = db.query(Role).join(UserRoleMapping).filter(
    UserRoleMapping.user_id.in_(user_ids)
).all()
```

---

### 9.2 Caching Strategy

#### Redis Caching

```python
# Cache user roles (TTL 5 minutes)
cache_key = f"user_roles:{user_id}"
roles = redis.get(cache_key)
if not roles:
    roles = get_user_roles_from_db(user_id)
    redis.setex(cache_key, 300, json.dumps(roles))

# Cache group membership (TTL 10 minutes)
cache_key = f"user_groups:{user_id}"
groups = redis.get(cache_key)
if not groups:
    groups = get_user_groups_from_db(user_id)
    redis.setex(cache_key, 600, json.dumps(groups))

# Cache role mappers (TTL 1 hour)
cache_key = f"role_mappers:{client_id}"
mappers = redis.get(cache_key)
if not mappers:
    mappers = get_role_mappers_from_db(client_id)
    redis.setex(cache_key, 3600, json.dumps(mappers))
```

#### Cache Invalidation

```python
# При изменении ролей пользователя
def assign_role_to_user(user_id, role_id):
    db.add(UserRoleMapping(user_id=user_id, role_id=role_id))
    db.commit()
    
    # Invalidate cache
    redis.delete(f"user_roles:{user_id}")
    redis.delete(f"user_groups:{user_id}")  # Might need group role refresh
    audit_log.log_role_assignment(user_id, role_id)
```

---

### 9.3 JWT Generation Performance

#### Target Metrics

| Метрика | Target | Current |
|---------|--------|---------|
| JWT generation time | < 50ms (p95) | 20-30ms |
| Role lookup time | < 30ms (p95) | TBD |
| Mapper application time | < 20ms (p95) | TBD |
| Group resolution time | < 50ms (p95) | TBD |

#### Optimization Techniques

```python
# Batch loading (avoid N+1)
user_roles = db.query(Role).filter(Role.id.in_(role_ids)).all()

# Prefetch related data
query = db.query(User).options(
    joinedload(User.roles),
    joinedload(User.groups)
)

# Connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40
)
```

---

## 10. Testing Strategy

### 10.1 Unit Tests

**File: `tests/test_rbac_roles.py`**
```python
def test_assign_role_to_user():
    user = create_user()
    role = create_role("moderator")
    
    assign_role_to_user(user.id, role.id)
    
    assert user.roles.count() == 1
    assert user.roles[0].name == "moderator"

def test_prevent_duplicate_role_assignment():
    user = create_user()
    role = create_role("user")
    
    assign_role_to_user(user.id, role.id)
    
    with pytest.raises(IntegrityError):
        assign_role_to_user(user.id, role.id)
```

**File: `tests/test_rbac_jwt.py`**
```python
def test_jwt_contains_user_roles():
    user = create_user()
    user.roles = [create_role("user"), create_role("moderator")]
    
    token = generate_access_token(user.id, "codelab-flutter-app")
    payload = decode_jwt(token)
    
    assert "roles" in payload
    assert set(payload["roles"]) == {"user", "moderator"}

def test_jwt_includes_mapped_roles():
    user = create_user()
    user.roles = [create_role("user")]
    
    create_role_mapper(
        client_id="codelab-flutter-app",
        source_role="user",
        target_role="codelab-flutter-app:content-viewer"
    )
    
    token = generate_access_token(user.id, "codelab-flutter-app")
    payload = decode_jwt(token)
    
    assert payload["resource_access"]["codelab-flutter-app"]["roles"] == ["content-viewer"]
```

---

### 10.2 Integration Tests

**File: `tests/integration/test_rbac_full_flow.py`**
```python
def test_admin_assigns_role_jwt_updated():
    admin = create_admin_user()
    user = create_regular_user()
    
    # Admin assigns role
    response = client.post(
        f"/api/v1/admin/users/{user.id}/roles",
        json={"role_id": MODERATOR_ROLE_ID},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    
    # User login and get new token
    token_response = client.post(
        "/oauth/token",
        data={
            "grant_type": "password",
            "username": user.username,
            "password": "password123",
            "client_id": "codelab-flutter-app"
        }
    )
    
    token = token_response.json()["access_token"]
    payload = decode_jwt(token)
    
    # JWT should contain new role
    assert "moderator" in payload["roles"]
```

---

### 10.3 Security Tests

**File: `tests/security/test_rbac_security.py`**
```python
def test_regular_user_cannot_assign_roles():
    user = create_regular_user()
    target_user = create_another_user()
    
    response = client.post(
        f"/api/v1/admin/users/{target_user.id}/roles",
        json={"role_id": ADMIN_ROLE_ID},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    assert response.status_code == 403

def test_client_cannot_modify_jwt_roles():
    """Попытка подделать роли в JWT должна быть обнаружена"""
    original_token = get_valid_token()
    payload = decode_jwt_unverified(original_token)
    
    # Попытка добавить admin роль
    payload["roles"].append("admin")
    
    forged_token = encode_jwt_without_signature(payload)
    
    # JWT validation должна fail
    with pytest.raises(JWTError):
        decode_jwt(forged_token)
```

---

## 11. Examples

### 11.1 Пример 1: Назначение роли пользователю

```bash
# 1. Админ получает токен
curl -X POST http://localhost:8003/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "username=admin@codelab.local" \
  -d "password=admin_password" \
  -d "client_id=codelab-flutter-app"

# Результат:
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}

# 2. Админ назначает роль "moderator" пользователю
curl -X POST http://localhost:8003/api/v1/admin/users/550e8400-e29b-41d4-a716-446655440001/roles \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{"role_id": "550e8400-e29b-41d4-a716-446655440002"}'

# Результат:
{
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "role_id": "550e8400-e29b-41d4-a716-446655440002",
  "created_at": "2026-04-05T10:00:00Z"
}

# 3. Пользователь получает новый токен с ролью
curl -X POST http://localhost:8003/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "username=user@codelab.local" \
  -d "password=user_password" \
  -d "client_id=codelab-flutter-app"

# Результат (декодированный JWT):
{
  "iss": "https://auth.codelab.local",
  "sub": "550e8400-e29b-41d4-a716-446655440001",
  "scope": "api:read api:write",
  "roles": ["user", "moderator"],
  "client_id": "codelab-flutter-app"
}
```

---

### 11.2 Пример 2: Role Mappers

```bash
# 1. Админ создает role mapper
curl -X POST http://localhost:8003/api/v1/admin/clients/codelab-flutter-app/role-mappers \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "user_to_content_viewer",
    "mapper_type": "role_to_role",
    "config": {
      "source_role": "user",
      "target_role": "codelab-flutter-app:content-viewer"
    },
    "enabled": true,
    "priority": 0
  }'

# 2. Пользователь с ролью "user" получает токен
curl -X POST http://localhost:8003/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "username=user@codelab.local" \
  -d "password=password" \
  -d "client_id=codelab-flutter-app"

# Результат (декодированный JWT):
{
  "iss": "https://auth.codelab.local",
  "sub": "550e8400-e29b-41d4-a716-446655440001",
  "roles": ["user"],
  "resource_access": {
    "codelab-flutter-app": {
      "roles": ["content-viewer"]
    }
  },
  "client_id": "codelab-flutter-app"
}
```

---

### 11.3 Пример 3: Groups

```bash
# 1. Админ создает организацию
curl -X POST http://localhost:8003/api/v1/admin/groups \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/organization/acme-corp",
    "name": "Acme Corporation",
    "description": "Main organization"
  }'

# Результат:
{
  "id": "550e8400-e29b-41d4-a716-446655440010",
  "path": "/organization/acme-corp",
  "name": "Acme Corporation",
  "parent_id": null,
  "created_at": "2026-04-05T10:00:00Z"
}

# 2. Админ создает подгруппу (команду)
curl -X POST http://localhost:8003/api/v1/admin/groups \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/organization/acme-corp/teams/engineering",
    "name": "Engineering Team",
    "parent_id": "550e8400-e29b-41d4-a716-446655440010"
  }'

# 3. Админ добавляет пользователя в группу
curl -X POST http://localhost:8003/api/v1/admin/groups/550e8400-e29b-41d4-a716-446655440011/members \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440001",
    "role_in_group": "team-member"
  }'

# 4. Админ назначает роль группе
curl -X POST http://localhost:8003/api/v1/admin/groups/550e8400-e29b-41d4-a716-446655440011/roles \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"role_id": "550e8400-e29b-41d4-a716-446655440003"}'

# 5. Пользователь получает токен
curl -X POST http://localhost:8003/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "username=user@codelab.local" \
  -d "password=password" \
  -d "client_id=codelab-flutter-app"

# Результат (декодированный JWT):
{
  "iss": "https://auth.codelab.local",
  "sub": "550e8400-e29b-41d4-a716-446655440001",
  "roles": ["user"],
  "groups": [
    "/organization/acme-corp",
    "/organization/acme-corp/teams/engineering"
  ],
  "client_id": "codelab-flutter-app"
}
```

---

## 12. Диаграммы системы

### 12.1 ER Диаграмма (Entity-Relationship) — Phase 1-2

```mermaid
erDiagram
    USERS ||--o{ USER_ROLE_MAPPINGS : has
    ROLES ||--o{ USER_ROLE_MAPPINGS : assigned_to
    OAUTH_CLIENTS ||--o{ ROLE_MAPPERS : configured_with
    
    USERS {
        uuid id PK
        string username UK
        string email UK
        timestamp created_at
    }
    
    ROLES {
        uuid id PK
        string name UK
        string description
        boolean is_system_role
    }
    
    USER_ROLE_MAPPINGS {
        uuid id PK
        uuid user_id FK
        uuid role_id FK
        timestamp created_at
    }
    
    OAUTH_CLIENTS {
        uuid id PK
        string client_id UK
        string name
    }
    
    ROLE_MAPPERS {
        uuid id PK
        string client_id FK
        string name
        string mapper_type
        json config
        boolean enabled
    }
```

### 12.2 ER Диаграмма — Phase 3-4 (Groups + Composite Roles)

```mermaid
erDiagram
    GROUPS ||--o{ GROUPS : parent
    GROUPS ||--o{ GROUP_ROLE_MAPPINGS : has
    GROUPS ||--o{ USER_GROUP_MEMBERSHIPS : contains
    USERS ||--o{ USER_GROUP_MEMBERSHIPS : member_of
    ROLES ||--o{ GROUP_ROLE_MAPPINGS : mapped_to
    ROLES ||--o{ COMPOSITE_ROLE_MAPPINGS : parent
    ROLES ||--o{ COMPOSITE_ROLE_MAPPINGS : child
    
    GROUPS {
        uuid id PK
        string path UK
        string name
        uuid parent_id FK
        string description
    }
    
    USER_GROUP_MEMBERSHIPS {
        uuid id PK
        uuid user_id FK
        uuid group_id FK
        string role_in_group
    }
    
    GROUP_ROLE_MAPPINGS {
        uuid id PK
        uuid group_id FK
        uuid role_id FK
    }
    
    COMPOSITE_ROLE_MAPPINGS {
        uuid id PK
        uuid parent_role_id FK
        uuid child_role_id FK
    }
```

### 12.3 JWT Generation Sequence Diagram

```mermaid
sequenceDiagram
    participant Client as Client
    participant AuthService as Auth Service
    participant DB as PostgreSQL
    participant Redis as Redis

    Client->>AuthService: 1. POST /oauth/token
    activate AuthService
    
    AuthService->>DB: 2. SELECT user by username
    activate DB
    DB-->>AuthService: User found
    deactivate DB
    
    AuthService->>DB: 3. SELECT user_roles
    activate DB
    DB-->>AuthService: roles
    deactivate DB
    
    AuthService->>DB: 4. SELECT user_groups
    activate DB
    DB-->>AuthService: groups
    deactivate DB
    
    AuthService->>DB: 5. SELECT group_roles
    activate DB
    DB-->>AuthService: group_roles
    deactivate DB
    
    AuthService->>DB: 6. SELECT role_mappers
    activate DB
    DB-->>AuthService: mappers
    deactivate DB
    
    AuthService->>AuthService: 7. Expand composite roles
    AuthService->>AuthService: 8. Apply role mappers
    AuthService->>AuthService: 9. Build JWT payload
    AuthService->>AuthService: 10. Sign JWT (RS256)
    
    AuthService->>Redis: 11. Cache roles & groups
    activate Redis
    Redis-->>AuthService: OK
    deactivate Redis
    
    AuthService-->>Client: 12. Return access_token
    deactivate AuthService
```

### 12.4 Role Assignment Flow Diagram

```mermaid
graph LR
    A["Admin<br/>(Bearer Token)"]
    B["POST /api/v1/admin/users/{id}/roles"]
    C["Validate JWT<br/>Check admin role"]
    D["Check role exists<br/>Check no duplicate"]
    E["INSERT user_role_mapping"]
    F["INVALIDATE cache<br/>user_roles:{user_id}"]
    G["AUDIT LOG<br/>role_assigned"]
    H["Response 201"]
    
    A -->|1. Request| B
    B -->|2. Validate| C
    C -->|3. Service logic| D
    D -->|4. Persist| E
    E -->|5. Invalidate| F
    E -->|6. Log| G
    F -->|7. Return| H
    
    style A fill:#E1F5FF
    style C fill:#FFE0B2
    style E fill:#E8F5E9
    style G fill:#FFF3E0
```

### 12.5 RBAC System Architecture

```mermaid
graph TB
    subgraph Clients
        Flutter["Flutter Client<br/>(Mobile)"]
        Admin["Admin UI<br/>(Web)"]
    end
    
    subgraph AuthService
        OAuth["OAuth2 Endpoints<br/>- /oauth/token<br/>- /.well-known/jwks.json"]
        AdminAPI["Admin APIs<br/>- /api/v1/admin/roles<br/>- /api/v1/admin/groups<br/>- /api/v1/admin/mappers"]
        TokenSvc["Token Service<br/>- JWT Generation<br/>- Role Resolution"]
        RoleSvc["Role Service<br/>- User Roles<br/>- Composite Roles<br/>- Role Mappers"]
        GroupSvc["Group Service<br/>- Group Management<br/>- Membership<br/>- Role Inheritance"]
    end
    
    subgraph DataLayer
        PG["PostgreSQL<br/>- roles<br/>- groups<br/>- mappings<br/>- audit_logs"]
        RedisCache["Redis<br/>- user_roles<br/>- user_groups<br/>- role_mappers<br/>- jwks"]
    end
    
    subgraph ResourceServers
        Core["Core Service<br/>- Validate JWT<br/>- Check roles"]
        LLM["LLM Proxy<br/>- Validate JWT<br/>- Check roles"]
    end
    
    Flutter -->|Login| OAuth
    Admin -->|Manage RBAC| AdminAPI
    OAuth -->|Generate| TokenSvc
    AdminAPI -->|Manage| RoleSvc
    AdminAPI -->|Manage| GroupSvc
    TokenSvc -->|Query| RoleSvc
    TokenSvc -->|Query| GroupSvc
    RoleSvc -->|Query| PG
    GroupSvc -->|Query| PG
    TokenSvc -->|Cache| RedisCache
    Flutter -->|Request with JWT| Core
    Flutter -->|Request with JWT| LLM
    Core -->|Validate JWT| RedisCache
    Core -->|Check roles| RoleSvc
    LLM -->|Validate JWT| RedisCache
    LLM -->|Check roles| RoleSvc
    
    style AuthService fill:#4A90E2,color:#fff
    style DataLayer fill:#50C878,color:#fff
    style ResourceServers fill:#FF6B6B,color:#fff
```

### 12.6 Group Hierarchy Example

```mermaid
graph TD
    Root["/organization/acme-corp"]
    
    subgraph Teams
        Eng["/organization/acme-corp/teams/engineering"]
        Sales["/organization/acme-corp/teams/sales"]
        Mgmt["/organization/acme-corp/teams/management"]
    end
    
    subgraph EngProjects
        Backend["/organization/acme-corp/teams/engineering/projects/backend"]
        Frontend["/organization/acme-corp/teams/engineering/projects/frontend"]
    end
    
    subgraph Users
        User1["👤 Alice (team-lead)<br/>roles: moderator, content-manager"]
        User2["👤 Bob (team-member)<br/>roles: content-viewer"]
        User3["👤 Carol (manager)<br/>roles: admin"]
    end
    
    Root -->|parent| Eng
    Root -->|parent| Sales
    Root -->|parent| Mgmt
    Eng -->|parent| Backend
    Eng -->|parent| Frontend
    
    User1 -->|member of| Eng
    User1 -->|member of| Backend
    User2 -->|member of| Eng
    User2 -->|member of| Backend
    User3 -->|member of| Root
    
    style Root fill:#E3F2FD
    style Eng fill:#F3E5F5
    style Sales fill:#F3E5F5
    style Mgmt fill:#F3E5F5
    style Backend fill:#E8F5E9
    style Frontend fill:#E8F5E9
    style User1 fill:#FFF3E0
    style User2 fill:#FFF3E0
    style User3 fill:#FFE0B2
```

---

## 13. References

### 12.1 Документация

- [`codelab-auth-service/docs/TECHNICAL_SPECIFICATION.md`](TECHNICAL_SPECIFICATION.md) — основная спецификация auth service
- [`codelab-auth-service/docs/IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) — план реализации
- [`codelab-auth-service/docs/API_DOCUMENTATION.md`](API_DOCUMENTATION.md) — документация API

### 12.2 Внешние ресурсы

- [Keycloak RBAC Documentation](https://www.keycloak.org/)
- [OAuth 2.0 Authorization Framework](https://tools.ietf.org/html/rfc6749)
- [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html)
- [UMA 2.0 Specification](https://docs.kantarainitiative.org/uma/wg/core/1.0/uma-core-2.0.html)

### 12.3 Рекомендуемые статьи

- "Role-Based Access Control" (NIST FIPS 180-4)
- "Fine-Grained Authorization in Microservices" (O'Reilly)
- "JWT Best Practices" (jwt.io)

---

## 13. FAQ

### Q: Зачем нужны и роли и разрешения?

**A:** Роли — это "кто" (пользователь, админ), разрешения — это "что" (читать, писать). Разделение упрощает управление:
- Роль `editor` может иметь разрешения `project:read` и `project:write`
- Роль `viewer` может иметь только `project:read`

---

### Q: Как обрабатывать глубокую иерархию групп?

**A:** Используем path-based идентификацию:
- `/organization/acme-corp` — организация (level 1)
- `/organization/acme-corp/department/engineering` — отдел (level 2)
- `/organization/acme-corp/department/engineering/team/backend` — команда (level 3)

Максимум 5 уровней рекомендуется.

---

### Q: Как избежать JWT bloat?

**A:** Несколько стратегий:
1. Ограничить количество ролей (max 50 в JWT)
2. Использовать reference ID вместо полного имени
3. Кэшировать expanded roles на клиентской стороне
4. Использовать refresh token для получения актуальных ролей

---

### Q: Как мигрировать существующих пользователей?

**A:** Пошаговая миграция:
1. Создать роль `user` в БД
2. Назначить всем пользователям роль `user`
3. Создать организационные группы
4. Постепенно добавлять пользователей в группы
5. Назначать роли группам (вместо прямого назначения)

---

## 14. Контакты и поддержка

**Разработчик:** Sergey Penkovsky  
**Email:** sergey.penkovsky@gmail.com  
**Проект:** CodeLab  
**Версия документа:** 2.0.0  
**Дата:** 2026-04-05  
**Статус:** 📋 Спецификация (перед реализацией)
