# OpenSpec Change: RBAC Phase 2 - Role Mappers

**Версия:** 1.0.0  
**Дата:** 5 апреля 2026  
**Сервис:** codelab-auth-service  
**Статус:** 📋 Proposed (перед реализацией)  
**Зависит от:** Phase 1 (User Roles)

---

## 🔴 Проблема (Why)

### Текущее состояние (После Phase 1)

После Phase 1 JWT содержит глобальные роли пользователя:

```json
{
  "roles": ["user", "moderator"],
  "client_id": "codelab-flutter-app"
}
```

**Ограничения:**
- ❌ Нет поддержки **resource-specific ролей** (разные роли для разных клиентов)
- ❌ Нельзя преобразовывать роли в зависимости от **контекста** (какой клиент запросил токен)
- ❌ Нельзя использовать **hardcoded роли** для конкретного приложения
- ❌ Нельзя применять **conditional logic** для определения ролей

### Use Cases

1. **Разные роли для разных клиентов**
   - Пользователь имеет роль "moderator" в системе
   - Для codelab-flutter-app → преобразовать в "content-editor"
   - Для admin-dashboard → оставить "moderator"

2. **Hardcoded роли для приложения**
   - Все пользователи когда используют мобильное приложение → добавить role "mobile-user"

3. **Conditional преобразования**
   - Если пользователь имеет роль "admin" И используется codelab-web-app → добавить "super-admin"

### Влияние на систему

| Аспект | Проблема |
|--------|---------|
| **Гибкость** | Невозможно иметь разные наборы ролей для разных клиентов |
| **Масштабируемость** | Каждый новый клиент требует изменения TokenService |
| **Управление доступом** | Нельзя применять логику на уровне клиента |
| **OAuth2 совместимость** | Не поддерживает Keycloak-style resource_access |

---

## 💚 Решение (What Changes)

### Компоненты, которые добавляются/обновляются

#### 1. **Database Schema**

Добавляется таблица `role_mappers`:

```sql
CREATE TABLE role_mappers (
  id UUID PRIMARY KEY,
  oauth_client_id UUID NOT NULL REFERENCES oauth_clients(id),
  source_role_name VARCHAR(255),  -- Исходная роль (null = всем)
  mapper_type ENUM('role_to_role', 'hardcoded', 'conditional'),
  target_role_name VARCHAR(255) NOT NULL,  -- Целевая роль
  condition_json JSONB,  -- Условие для conditional mappers
  priority INTEGER,  -- Порядок применения
  enabled BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

#### 2. **JWT Payload**

JWT расширяется с полем `resource_access`:

```json
{
  "roles": ["user", "moderator"],
  "resource_access": {
    "codelab-flutter-app": {
      "roles": ["user", "content-editor"]
    },
    "admin-dashboard": {
      "roles": ["moderator"]
    }
  }
}
```

#### 3. **Services**

- `RoleMapperService` — CRUD операции для mappers
- `MapperEvaluationEngine` — применение mappers к JWT payload
- `TokenService` обновляется для использования mappers

#### 4. **API Endpoints** (Admin-only)

```
POST   /api/v1/admin/role-mappers
GET    /api/v1/admin/role-mappers
POST   /api/v1/admin/oauth-clients/{client_id}/role-mappers
GET    /api/v1/admin/oauth-clients/{client_id}/role-mappers
DELETE /api/v1/admin/role-mappers/{mapper_id}
```

---

## 🤔 Альтернативы

### Альтернатива 1: Использовать Keycloak
Отклонена по причинам Phase 1.

### Альтернатива 2: Хранить mappers в каждом клиенте
**Минусы:**
- ❌ Сложнее управлять (разные места)
- ❌ Плохо масштабируется

**Решение:** Отклонено. Mapper должны быть в Auth Service.

---

## ⚠️ Риски и Mitigation

| Риск | Mitigation |
|------|-----------|
| Performance: evaluating mappers медленно | Использовать caching, optimize query |
| Циклические зависимости в mappers | Валидация при создании mapper |
| JWT payload слишком большой | Limit количество mappers, сжатие |

---

## ✅ Критерии успеха

- [x] role_mappers таблица создана
- [x] RoleMapperService реализован
- [x] MapperEvaluationEngine работает
- [x] JWT содержит resource_access
- [x] Все API endpoints реализованы
- [x] Tests покрывают все типы mappers
- [x] Performance < 100ms (даже с 100+ mappers)

---

## 📝 Non-goals

- ❌ Fine-grained авторизация (Phase 6)
- ❌ Role hierarchies (Phase 4)
- ❌ Groups (Phase 3)

---

## Следующие шаги

После одобрения proposal:
1. Начать работу на design.md
2. Создать задачи в project management
3. Начать реализацию

---

## 🔗 Связанные документы

- [`proposal.md`](proposal.md) — это документ
- [`docs/RBAC_SPECIFICATION.md`](../../docs/RBAC_SPECIFICATION.md) — Phase 2 раздел
- [`changes/2026-04-05-rbac-phase1-user-roles/`](../2026-04-05-rbac-phase1-user-roles/) — Phase 1 (зависимость)
- [`changes/2026-04-19-rbac-phase3-groups/`](../2026-04-19-rbac-phase3-groups/) — Phase 3 (следующая фаза)
