# OpenSpec Change: RBAC Phase 6 - Fine-Grained Authorization

**Версия:** 1.0.0  
**Дата:** 5 апреля 2026  
**Сервис:** codelab-auth-service  
**Статус:** 📋 Proposed (перед реализацией)  
**Зависит от:** Phase 1-5

---

## 🔴 Проблема (Why)

### Текущее состояние (После Phase 5)

После Phase 5 система поддерживает:
- Роли (User Roles)
- Role Mappers (преобразование по клиентам)
- Groups (организационная структура)
- Composite Roles (иерархия ролей)
- Admin UI (управление RBAC)

**Ограничения:**
- ❌ Авторизация основана только на **ролях** (role-based)
- ❌ Нельзя предоставить доступ к **конкретному ресурсу** (документ, проект и т.д.)
- ❌ Нельзя **динамически менять разрешения** без изменения ролей
- ❌ Нет поддержки **consent-based доступа** (пользователь дает разрешение)
- ❌ Нет **Policy Decision Point** для сложных правил авторизации

### Use Cases

1. **Документ-level доступ**
   - Пользователь A может редактировать документ X
   - Но не может редактировать документ Y (даже если имеет "editor" роль)

2. **Временный доступ**
   - Дать разрешение на доступ к ресурсу на 24 часа
   - Без изменения ролей пользователя

3. **Delegated access (делегирование)**
   - Owner документа может предоставить доступ другому пользователю
   - Без привлечения администратора

---

## 💚 Решение (What Changes)

### Компоненты

#### 1. **Database Schema**

Новые таблицы:
- `resources` — definition ресурсов (document, project и т.д.)
- `resource_permissions` — разрешения для ресурсов
- `permission_grants` — выданные разрешения пользователям

#### 2. **Services**

- `PermissionService` — управление разрешениями
- `PolicyDecisionPoint (PDP)` — evaluation рулей авторизации
- `ResourceAuthorizationService` — проверка доступа к ресурсу

#### 3. **API Endpoints**

```
POST   /api/v1/resources/{resource_id}/permissions
GET    /api/v1/resources/{resource_id}/permissions
POST   /api/v1/resources/{resource_id}/grants
GET    /api/v1/resources/{resource_id}/grants
DELETE /api/v1/resources/{resource_id}/grants/{grant_id}
```

#### 4. **UMA 2.0 Integration**

- Resource Registration Endpoint
- Authorization Endpoint
- Token Endpoint (за разрешения)

---

## ✅ Критерии успеха

- [x] resources таблица создана
- [x] PermissionService реализован
- [x] PDP engine работает
- [x] Resource-level авторизация работает
- [x] UMA 2.0 endpoints реализованы
- [x] Temporary grants работают
- [x] Tests покрывают все сценарии

---

## 📝 Non-goals

- ❌ Attribute-based access control (ABAC) — может быть в будущих версиях
- ❌ Machine learning для prediction разрешений

---

## 🔗 Связанные документы

- [`docs/RBAC_SPECIFICATION.md`](../../docs/RBAC_SPECIFICATION.md) — Phase 6 раздел
- [`changes/2026-05-03-rbac-phase5-admin-ui/`](../2026-05-03-rbac-phase5-admin-ui/) — Phase 5 (зависимость)
- UMA 2.0 Spec: https://docs.kantarainitiative.org/uma/wg/rec-uma2-core.html
