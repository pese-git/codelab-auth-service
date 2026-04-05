# OpenSpec Change: RBAC Phase 5 - Admin UI Integration

**Версия:** 1.0.0  
**Дата:** 5 апреля 2026  
**Сервис:** codelab-admin-frontend (интеграция с codelab-auth-service)  
**Статус:** 📋 Proposed (перед реализацией)

---

## 🔴 Проблема (Why)

### Текущее состояние (После Phase 4)

После Phase 4 система поддерживает все RBAC компоненты через API, но управление ими возможно только через:
- curl команды
- REST API клиент (Postman и т.д.)
- Прямые обращения к БД

**Ограничения:**
- ❌ Нет **графического интерфейса** для управления RBAC
- ❌ Нельзя **визуализировать иерархии** ролей и групп
- ❌ Нельзя **тестировать роли** перед применением
- ❌ Нет **audit логирования** в UI

### Use Cases

1. **Admin хочет создать новую роль**
   - Кликнуть "Create Role"
   - Заполнить форму (name, display_name, description)
   - Увидеть список существующих ролей

2. **Admin хочет организовать иерархию групп**
   - Визуальное дерево: /organization → /teams → /engineering
   - Drag-and-drop для создания структуры

3. **Admin хочет проверить какие роли получит пользователь**
   - "Test User Roles" interface
   - Выбрать пользователя → увидеть все применяемые роли

---

## 💚 Решение (What Changes)

### Компоненты

#### 1. **Admin UI Pages**

- **Roles Management**
  - Create, Read, Update, Delete roles
  - Filter by system_defined/custom
  - Search roles

- **Groups Management**
  - Hierarchical tree visualization
  - Add/remove group members
  - Edit group properties

- **Role Mappers**
  - Create/edit/delete mappers
  - Visual editor for mapper conditions
  - Test mapper evaluation

- **User Roles**
  - Assign/remove roles to users
  - Bulk user role assignment
  - Search and filter

- **Audit Log**
  - View all RBAC changes
  - Filter by date, user, action
  - Export to CSV

#### 2. **API Changes**

Новые endpoints для поддержки UI:
```
GET /api/v1/admin/rbac/audit-log
GET /api/v1/admin/rbac/test-roles/{user_id}
POST /api/v1/admin/rbac/test-mappers
```

#### 3. **UI Components**

- RoleForm (create/edit role)
- GroupTree (hierarchical visualization)
- MapperEditor (WYSIWYG mapper builder)
- AuditLog (searchable table)
- RoleTestSandbox (test roles before applying)

---

## ✅ Критерии успеха

- [x] Все RBAC функции доступны в UI
- [x] Иерархии визуализируются красиво
- [x] Есть валидация form данных на клиенте
- [x] Audit log работает и фильтруется
- [x] Тестирование ролей работает
- [x] UI responsivе (работает на мобиле)
- [x] Все API интегрированы

---

## 🔗 Связанные документы

- [`docs/RBAC_SPECIFICATION.md`](../../docs/RBAC_SPECIFICATION.md) — Phase 5 раздел
- [`changes/2026-04-26-rbac-phase4-composite-roles/`](../2026-04-26-rbac-phase4-composite-roles/) — Phase 4 (зависимость)
- [`changes/2026-05-10-rbac-phase6-fine-grained-authz/`](../2026-05-10-rbac-phase6-fine-grained-authz/) — Phase 6 (следующая фаза)
