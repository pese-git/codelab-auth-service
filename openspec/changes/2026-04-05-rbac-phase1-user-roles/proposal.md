# OpenSpec Change: RBAC Phase 1 - User Roles Management

**Версия:** 1.0.0  
**Дата:** 5 апреля 2026  
**Сервис:** codelab-auth-service  
**Статус:** 📋 Proposed (перед реализацией)

---

## 🔴 Проблема (Why)

### Текущее состояние

В текущей реализации CodeLab Auth Service используется только **scope-based авторизация**:

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "scope": "api:read api:write",
  "client_id": "codelab-flutter-app"
}
```

**Ограничения:**
- ❌ Нет поддержки **ролей** (admin, user, moderator и т.д.)
- ❌ Нет различия между различными **уровнями доступа** для одного пользователя
- ❌ **Масштабирование разрешений** невозможно без изменения scope в JWT
- ❌ **Централизованное управление правами** отсутствует
- ❌ Нет поддержки **группообразных ролей** (team lead, content manager и т.д.)
- ❌ Сложно реализовать **специфичные для ресурса** роли (resource_access)

### Влияние на систему

| Аспект | Проблема |
|--------|---------|
| **Администрирование** | Admin должен вручную изменять JWT payload для добавления прав |
| **Безопасность** | Нет granular контроля доступа (всё по scope-ам) |
| **Масштабируемость** | Каждое добавление нового уровня прав требует изменения scope |
| **API Дизайн** | Отсутствует стандартный механизм для role-based авторизации |
| **Roadmap** | Невозможно реализовать Phase 2-6 RBAC без Phase 1 |

### Бизнес-причины

- 🎯 **Управление контентом** — разные роли (editor, viewer, reviewer) нужны для управления контентом в CodeLab
- 🎯 **Командная работа** — поддержка team-based ролей для совместной разработки
- 🎯 **Соответствие стандартам** — OAuth2 + RBAC — промышленный стандарт для авторизации

---

## 💚 Решение (What Changes)

### Компоненты, которые добавляются/обновляются

#### 1. **Database Schema**
Добавляются две новые таблицы:

**`roles` таблица:**
```sql
CREATE TABLE roles (
  id UUID PRIMARY KEY,
  name VARCHAR(255) NOT NULL UNIQUE,  -- "admin", "user", "moderator"
  display_name VARCHAR(255),
  description TEXT,
  system_defined BOOLEAN DEFAULT FALSE,  -- true для предустановленных ролей
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

**`user_role_mappings` таблица:**
```sql
CREATE TABLE user_role_mappings (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  created_at TIMESTAMP,
  UNIQUE(user_id, role_id)
);
```

#### 2. **Models** (SQLAlchemy)
- `Role` model с полями: id, name, display_name, description, system_defined
- `UserRoleMapping` model с foreign keys на User и Role

#### 3. **Services**
- `RoleService` — CRUD операции для ролей
- `UserRoleService` — управление ролями пользователей
- `TokenService` обновляется для добавления roles в JWT payload

#### 4. **API Endpoints** (Admin-only, require `admin` scope)
```
POST   /api/v1/admin/roles                    — создать роль
GET    /api/v1/admin/roles                    — список ролей
GET    /api/v1/admin/roles/{role_id}          — получить роль
PUT    /api/v1/admin/roles/{role_id}          — обновить роль
DELETE /api/v1/admin/roles/{role_id}          — удалить роль

POST   /api/v1/admin/users/{user_id}/roles    — добавить роль пользователю
GET    /api/v1/admin/users/{user_id}/roles    — список ролей пользователя
DELETE /api/v1/admin/users/{user_id}/roles/{role_name} — удалить роль
```

#### 5. **JWT Integration**
JWT payload расширяется с новым полем `roles`:

```json
{
  "iss": "https://auth.codelab.local",
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "scope": "api:read api:write",
  "roles": ["user", "moderator"],
  "client_id": "codelab-flutter-app"
}
```

#### 6. **Migration & Seed Data**
- Alembic миграция для создания таблиц и индексов
- Seed скрипт для создания предустановленных ролей (admin, user, moderator)

#### 7. **Backward Compatibility**
- Существующий scope field сохраняется в JWT
- Клиенты, которые используют scope, продолжают работать
- Новые клиенты могут использовать roles вместо/вместе со scope

---

## 🤔 Альтернативы

### Альтернатива 1: Использовать готовый Keycloak
**Плюсы:**
- ✅ Production-ready решение
- ✅ Встроенная UI для управления RBAC
- ✅ Лучше документировано

**Минусы:**
- ❌ Избыточная сложность для MVP
- ❌ Требует дополнительной инфраструктуры
- ❌ Сложнее интегрировать с существующим Auth Service

**Решение:** Отклонено. Будем использовать custom implementation, но совместимую с Keycloak API.

### Альтернатива 2: Хранить роли в JWT только (без БД)
**Плюсы:**
- ✅ Простая реализация
- ✅ Нет необходимости в миграциях

**Минусы:**
- ❌ Невозможно управлять ролями в runtime
- ❌ Требует пересоздания JWT для изменения ролей
- ❌ Плохая масштабируемость

**Решение:** Отклонено. Нужна БД для управления ролями.

### Альтернатива 3: Использовать Permission-based подход вместо Role-based
**Плюсы:**
- ✅ Более гибкий (fine-grained)
- ✅ Лучше для комплексных систем

**Минусы:**
- ❌ Слишком сложно для Phase 1
- ❌ Требует более сложной БД схемы
- ❌ Может быть реализовано как Phase 6 (Fine-Grained Authz)

**Решение:** Отклонено для Phase 1. Оставляем как future enhancement (Phase 6).

---

## ⚠️ Риски и Mitigation

| Риск | Вероятность | Влияние | Mitigation |
|------|------------|--------|-----------|
| **Performance**: N+1 queries при получении ролей пользователя | Средняя | Высокое | Использовать eager loading (SELECT ... JOIN user_role_mappings) |
| **Data Consistency**: Orphaned role assignments при удалении ролей | Низкая | Высокое | Использовать ON DELETE CASCADE в БД constraints |
| **Security**: Unauthorized access к role management endpoints | Средняя | Критическое | Требовать `admin` scope для всех role-related endpoints, логировать все изменения |
| **Backward Compatibility**: Старые клиенты не поддерживают roles в JWT | Высокая | Среднее | Сохранить scope field, выпустить миграционный гайд |
| **Database Migration**: Неудачная миграция на production | Низкая | Критическое | Тестировать миграции на staging, иметь rollback план |

---

## ✅ Критерии успеха

### Функциональные критерии
- [x] Таблицы `roles` и `user_role_mappings` созданы и работают
- [x] RoleService и UserRoleService полностью реализованы с тестами
- [x] Все 8 API endpoints реализованы и задокументированы
- [x] JWT payload содержит поле `roles` с корректными значениями
- [x] Migration работает forward и backward (rollback)
- [x] Все edge cases обработаны (удаление роли, удаление пользователя и т.д.)

### Нефункциональные критерии
- [x] Код покрыт тестами (pytest) минимум на 85%
- [x] API документирована в OpenAPI/Swagger
- [x] Все docstrings на русском языке
- [x] Нет breaking changes для существующих клиентов
- [x] Performance: получение ролей пользователя < 100ms (на staging)

### Acceptance criteria
- [x] PR reviews пройдены минимум двумя code reviewers
- [x] Все тесты проходят в CI/CD pipeline
- [x] Интеграционные тесты с TokenService проходят
- [x] Документация обновлена в docs/RBAC_SPECIFICATION.md

---

## 📊 Метрики

### Успеха реализации
- ✅ **Time to Complete**: 2-3 недели (от предложения до production)
- ✅ **Test Coverage**: ≥ 85% на код phase 1
- ✅ **API Response Time**: < 100ms для любого role-related endpoint
- ✅ **Documentation Completeness**: 100% endpoints documented, с curl examples

### Долгосрочные метрики (после deployment)
- 📈 **Role Assignment Rate**: сколько пользователей имеют роли != "user"
- 📈 **Role Change Rate**: сколько role assignments создается/удаляется в день
- 📈 **JWT Token Size**: убедиться, что добавление `roles` не увеличивает size слишком много

---

## 📝 Non-goals

- ❌ Fine-grained авторизация (это Phase 6)
- ❌ Интеграция с внешними RBAC системами (например, LDAP)
- ❌ Admin UI для управления ролями (это Phase 5)
- ❌ Role hierarchies/composition (это Phase 4)
- ❌ Permission-based авторизация (это Phase 6)

---

## 🔗 Связанные документы

- [`docs/RBAC_SPECIFICATION.md`](../../docs/RBAC_SPECIFICATION.md) — полная спецификация RBAC
- [`docs/TECHNICAL_SPECIFICATION.md`](../../docs/TECHNICAL_SPECIFICATION.md) — техническое задание для Auth Service
- [`openspec/changes/2026-04-12-rbac-phase2-role-mappers/`](../2026-04-12-rbac-phase2-role-mappers/) — Phase 2 (Role Mappers)
- [`openspec/changes/2026-04-19-rbac-phase3-groups/`](../2026-04-19-rbac-phase3-groups/) — Phase 3 (Groups)

---

## Следующие шаги

После одобрения proposal:
1. Начать работу на design.md (детальная архитектура)
2. Создать задачи в project management системе
3. Начать реализацию согласно tasks.md
