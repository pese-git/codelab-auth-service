# OpenSpec Change: RBAC Phase 3 - Hierarchical Groups

**Версия:** 1.0.0  
**Дата:** 5 апреля 2026  
**Сервис:** codelab-auth-service  
**Статус:** 📋 Proposed (перед реализацией)  
**Зависит от:** Phase 1, Phase 2

---

## 🔴 Проблема (Why)

### Текущее состояние (После Phase 2)

После Phase 2 система поддерживает:
- Пользовательские роли (User Roles)
- Role Mappers для преобразования ролей по клиентам

**Ограничения:**
- ❌ Нет **организационной структуры** (teams, departments и т.д.)
- ❌ Нельзя выражать **иерархические отношения** (parent groups, subgroups)
- ❌ Нет **path-based идентификации** (/org/teams/engineering)
- ❌ Нельзя наследовать роли от групп (/org → inherit admin, /org/teams/engineering → inherit moderator)
- ❌ Нет поддержки **группами в JWT**

### Use Cases

1. **Организационная иерархия**
   ```
   /organization
   ├── /organization/teams
   │   ├── /organization/teams/engineering
   │   ├── /organization/teams/marketing
   └── /organization/departments
       ├── /organization/departments/sales
   ```

2. **Наследование ролей**
   - Все в /organization/teams/engineering наследуют роль "engineer"
   - Все в /organization/teams наследуют роль "team-member"

3. **управление по группам**
   - /organization/teams/engineering может редактировать код
   - /organization/teams/marketing может редактировать контент

---

## 💚 Решение (What Changes)

### Компоненты, которые добавляются/обновляются

#### 1. **Database Schema**

Три новые таблицы:
- `groups` — определение групп с path
- `user_group_memberships` — принадлежность пользователей к группам
- `group_role_mappings` — роли групп (группа наследует роли)

#### 2. **JWT Payload**

JWT расширяется с полем `groups`:

```json
{
  "roles": ["user", "moderator"],
  "groups": [
    "/organization",
    "/organization/teams",
    "/organization/teams/engineering"
  ]
}
```

#### 3. **Services**

- `GroupService` — CRUD для групп
- `GroupHierarchyService` — работа с иерархией (parent, children, ancestors)
- `UserGroupService` — управление membership
- `TokenService` обновляется для добавления groups в JWT

#### 4. **API Endpoints** (Admin-only)

```
POST   /api/v1/admin/groups
GET    /api/v1/admin/groups
GET    /api/v1/admin/groups/{group_id}
PUT    /api/v1/admin/groups/{group_id}
DELETE /api/v1/admin/groups/{group_id}

POST   /api/v1/admin/users/{user_id}/groups
GET    /api/v1/admin/users/{user_id}/groups
DELETE /api/v1/admin/users/{user_id}/groups/{group_id}
```

---

## ⚠️ Риски и Mitigation

| Риск | Mitigation |
|------|-----------|
| Сложная иерархия (deep nesting) | Limit depth (max 10 levels), optimize queries |
| Циклические ссылки (A → B, B → A) | Валидация при создании groups |
| Performance на большом количестве групп | Кеширование иерархии, индексы на path |

---

## ✅ Критерии успеха

- [x] groups таблица с path идентификацией
- [x] user_group_memberships таблица
- [x] GroupService и GroupHierarchyService реализованы
- [x] JWT содержит groups field
- [x] Path-based queries работают быстро (< 50ms)
- [x] Все API endpoints реализованы
- [x] Tests покрывают иерархию и наследование

---

## 📝 Non-goals

- ❌ Fine-grained авторизация (Phase 6)
- ❌ Composite roles (Phase 4)
- ❌ Admin UI (Phase 5)

---

## Следующие шаги

После одобрения proposal:
1. Начать работу на design.md
2. Создать задачи
3. Реализация

---

## 🔗 Связанные документы

- [`proposal.md`](proposal.md) — это документ
- [`docs/RBAC_SPECIFICATION.md`](../../docs/RBAC_SPECIFICATION.md) — Phase 3 раздел
- [`changes/2026-04-05-rbac-phase1-user-roles/`](../2026-04-05-rbac-phase1-user-roles/) — Phase 1 (зависимость)
- [`changes/2026-04-12-rbac-phase2-role-mappers/`](../2026-04-12-rbac-phase2-role-mappers/) — Phase 2 (зависимость)
- [`changes/2026-04-26-rbac-phase4-composite-roles/`](../2026-04-26-rbac-phase4-composite-roles/) — Phase 4 (следующая фаза)
