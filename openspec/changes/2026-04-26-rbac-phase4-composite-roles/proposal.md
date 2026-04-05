# OpenSpec Change: RBAC Phase 4 - Composite Roles

**Версия:** 1.0.0  
**Дата:** 5 апреля 2026  
**Сервис:** codelab-auth-service  
**Статус:** 📋 Proposed (перед реализацией)  
**Зависит от:** Phase 1, Phase 2, Phase 3

---

## 🔴 Проблема (Why)

### Текущее состояние (После Phase 3)

После Phase 3 система поддерживает:
- User Roles (базовые роли)
- Role Mappers (преобразование по клиентам)
- Groups (организационная структура)

**Ограничения:**
- ❌ Нельзя создавать **иерархии ролей** (роль содержит другие роли)
- ❌ Нельзя выражать **сложные наборы разрешений** через роли
- ❌ Нет **наследования разрешений** через иерархию ролей

### Use Cases

1. **Композитная роль "team-lead"**
   - "team-lead" = "moderator" + "team-member" + "reviewer"
   - Пользователь с "team-lead" автоматически имеет все эти роли

2. **Иерархия должностей**
   - "director" = "manager" (которая = "supervisor" + "employee")
   - Все разрешения наследуются вверх/вниз по иерархии

---

## 💚 Решение (What Changes)

### Компоненты

#### 1. **Database Schema**

Новая таблица:
- `role_compositions` — связи роль → роль для иерархии

#### 2. **JWT Payload**

```json
{
  "roles": ["user", "moderator"],
  "composite_roles": ["team-lead", "content-manager"]
}
```

#### 3. **Services**

- `RoleCompositionService` — управление иерархией ролей
- `RoleResolutionEngine` — рекурсивное разрешение ролей

#### 4. **API Endpoints**

```
POST   /api/v1/admin/roles/{role_id}/composition
GET    /api/v1/admin/roles/{role_id}/composition
DELETE /api/v1/admin/roles/{role_id}/composition/{child_role_id}
```

---

## ✅ Критерии успеха

- [x] role_compositions таблица создана
- [x] RoleCompositionService реализован
- [x] Circular dependency prevention работает
- [x] JWT содержит composite_roles field
- [x] Role resolution algorithm работает правильно
- [x] Tests покрывают рекурсивное разрешение

---

## 🔗 Связанные документы

- [`docs/RBAC_SPECIFICATION.md`](../../docs/RBAC_SPECIFICATION.md) — Phase 4 раздел
- [`changes/2026-04-19-rbac-phase3-groups/`](../2026-04-19-rbac-phase3-groups/) — Phase 3 (зависимость)
- [`changes/2026-05-03-rbac-phase5-admin-ui/`](../2026-05-03-rbac-phase5-admin-ui/) — Phase 5 (следующая фаза)
