# Tasks: RBAC Phase 1 - User Roles Management

**Версия:** 1.0.0  
**Дата:** 5 апреля 2026  
**Статус:** 📋 Task List

---

## Общая информация

**Estimated Total Effort:** 2-3 недели (depending on team size)  
**Team Size:** 2-3 developers  
**Dependencies:** None (может быть запущена параллельно с Phase 2)

---

## Task List

### 1. Database Schema & Migrations

#### 1.1 Create Alembic Migration for roles table
**Priority:** Critical  
**Effort:** 4-6 hours  
**Owner:** Backend Developer  

**Description:**
Создать Alembic миграцию для таблицы roles с полями: id, name, display_name, description, system_defined, created_at, updated_at.

**Acceptance Criteria:**
- [x] Миграция создана в `migration/versions/`
- [x] Таблица roles создается с правильной схемой
- [x] Индекс на name создается
- [x] Индекс на system_defined создается
- [x] UNIQUE constraint на name работает
- [x] Миграция проверена и может быть откачена (downgrade)
- [x] Migration revision updated в alembic history

**Testing:**
```bash
# Forward migration
alembic upgrade head

# Verify table
SELECT * FROM roles;

# Backward migration
alembic downgrade -1
```

---

#### 1.2 Create Alembic Migration for user_role_mappings table
**Priority:** Critical  
**Effort:** 4-6 hours  
**Owner:** Backend Developer  

**Description:**
Создать Alembic миграцию для таблицы user_role_mappings с foreign keys на users и roles таблицы.

**Acceptance Criteria:**
- [x] Миграция создана
- [x] Foreign key constraints установлены (ON DELETE CASCADE)
- [x] UNIQUE constraint (user_id, role_id) работает
- [x] Индексы на user_id и role_id создаются
- [x] Миграция может быть откачена
- [x] Не нарушает целостность данных с существующей users таблицей

---

#### 1.3 Seed Initial Roles
**Priority:** High  
**Effort:** 2-3 hours  
**Owner:** Backend Developer  

**Description:**
Создать seed скрипт/миграцию для вставки предустановленных ролей (admin, user, moderator).

**Acceptance Criteria:**
- [x] Скрипт создает 3 базовые роли (admin, user, moderator)
- [x] Каждая роль имеет system_defined=true
- [x] Скрипт идемпотентный (можно запустить дважды без ошибок)
- [x] Данные проверяются в тестах

---

### 2. SQLAlchemy Models

#### 2.1 Create Role Model
**Priority:** Critical  
**Effort:** 3-4 hours  
**Owner:** Backend Developer  

**Description:**
Создать SQLAlchemy Model для таблицы roles с полями, отношениями и методами.

**Acceptance Criteria:**
- [x] Role model с полями id, name, display_name, description, system_defined
- [x] Отношение к UserRoleMapping (one-to-many)
- [x] Все поля имеют type hints
- [x] Docstring объясняет назначение модели
- [x] Модель наследует от Base
- [x] Использует UUID для id

**Code Quality:**
- Русский язык в docstrings
- Type hints для всех атрибутов
- Логичное именование переменных

---

#### 2.2 Create UserRoleMapping Model
**Priority:** Critical  
**Effort:** 3-4 hours  
**Owner:** Backend Developer  

**Description:**
Создать UserRoleMapping model для таблицы user_role_mappings.

**Acceptance Criteria:**
- [x] UserRoleMapping model с полями id, user_id, role_id, created_at
- [x] Foreign keys на User и Role
- [x] Отношения к User и Role models
- [x] UNIQUE constraint на (user_id, role_id)
- [x] Все type hints в порядке

---

#### 2.3 Update User Model
**Priority:** Critical  
**Effort:** 2-3 hours  
**Owner:** Backend Developer  

**Description:**
Обновить User model для добавления отношения к UserRoleMapping и свойства roles.

**Acceptance Criteria:**
- [x] Добавлено отношение user_role_mappings
- [x] Добавлено свойство @property roles которое возвращает список имен ролей
- [x] Backward compatibility сохранена (старые поля не изменены)
- [x] Tests обновлены

---

### 3. Services Implementation

#### 3.1 Implement RoleService (CRUD)
**Priority:** Critical  
**Effort:** 8-12 hours  
**Owner:** Backend Developer 1  

**Description:**
Реализовать RoleService с методами: create_role, get_role, get_role_by_name, list_roles, update_role, delete_role.

**Acceptance Criteria:**
- [x] Все 6 методов реализованы
- [x] Используются async/await
- [x] Type hints для всех параметров и возвращаемых значений
- [x] Docstrings объясняют каждый метод
- [x] Exception handling для всех error cases
- [x] Логирование для всех операций (INFO для успеха, ERROR для ошибок)
- [x] Tests покрывают 100% кода RoleService

**Error Handling:**
- RoleAlreadyExistsError — при попытке создать дублирующуюся роль
- RoleNotFoundError — при запросе несуществующей роли
- SystemRoleCannotBeDeletedError — при попытке удалить встроенную роль

---

#### 3.2 Implement UserRoleService
**Priority:** Critical  
**Effort:** 8-12 hours  
**Owner:** Backend Developer 1  

**Description:**
Реализовать UserRoleService с методами: assign_role, remove_role, get_user_roles, has_role.

**Acceptance Criteria:**
- [x] Все 4 метода реализованы
- [x] get_user_roles оптимизирован (selectinload, без N+1)
- [x] assign_role проверяет что пользователь и роль существуют
- [x] assign_role проверяет что пользователь не уже имеет роль
- [x] remove_role возвращает True/False
- [x] has_role работает правильно
- [x] Все операции логируются
- [x] Tests покрывают 100% кода

**Performance Requirements:**
- get_user_roles должна быть < 100ms (на staging)
- Не должна создавать N+1 queries

---

#### 3.3 Update TokenService to Include Roles
**Priority:** Critical  
**Effort:** 6-8 hours  
**Owner:** Backend Developer 2  

**Description:**
Обновить TokenService.create_access_token() для добавления roles в JWT payload.

**Acceptance Criteria:**
- [x] create_access_token получает роли пользователя из UserRoleService
- [x] Роли добавляются в JWT payload as массив
- [x] Если пользователь нет ролей, добавляется default role "user"
- [x] JWT payload содержит scope и roles одновременно (backward compatible)
- [x] Tests проверяют что JWT содержит правильные роли
- [x] Tests проверяют что старые клиенты без roles поддержки работают

**JWT Payload Example:**
```json
{
  "iss": "https://auth.codelab.local",
  "sub": "user_id",
  "scope": "api:read api:write",
  "roles": ["user", "moderator"],
  "client_id": "codelab-flutter-app",
  "iat": 1712300000,
  "exp": 1712303600
}
```

---

### 4. API Endpoints Implementation

#### 4.1 Implement Role Management Endpoints
**Priority:** Critical  
**Effort:** 8-12 hours  
**Owner:** Backend Developer 2  

**Description:**
Реализовать все 5 role management endpoints в FastAPI.

**Endpoints:**
```
POST   /api/v1/admin/roles              — create role
GET    /api/v1/admin/roles              — list roles
GET    /api/v1/admin/roles/{role_id}    — get role
PUT    /api/v1/admin/roles/{role_id}    — update role
DELETE /api/v1/admin/roles/{role_id}    — delete role
```

**Acceptance Criteria:**
- [x] Все 5 endpoints реализованы
- [x] Все endpoints требуют Bearer token с admin scope
- [x] Response schemas определены (Pydantic models)
- [x] Error responses соответствуют OAuth2 спецификации
- [x] Все endpoints логируют access
- [x] Endpoints документированы в OpenAPI/Swagger
- [x] curl examples работают

**Security:**
- Require admin scope для всех endpoints
- Validate input data (name max 255 chars и т.д.)
- Rate limiting on creation endpoints

---

#### 4.2 Implement User Role Endpoints
**Priority:** Critical  
**Effort:** 8-12 hours  
**Owner:** Backend Developer 2  

**Description:**
Реализовать все 3 user role endpoints в FastAPI.

**Endpoints:**
```
POST   /api/v1/admin/users/{user_id}/roles              — assign role
GET    /api/v1/admin/users/{user_id}/roles              — list user roles
DELETE /api/v1/admin/users/{user_id}/roles/{role_name}  — remove role
```

**Acceptance Criteria:**
- [x] Все 3 endpoints реализованы
- [x] POST возвращает 201 Created
- [x] GET возвращает список ролей в правильном формате
- [x] DELETE возвращает 204 No Content
- [x] Все endpoints требуют admin scope
- [x] Error responses правильные (404 для неэксисдующего пользователя и т.д.)
- [x] Endpoints документированы

---

### 5. Testing

#### 5.1 Unit Tests for RoleService
**Priority:** High  
**Effort:** 6-8 hours  
**Owner:** Backend Developer 1  

**Description:**
Написать unit tests для всех методов RoleService.

**Test Cases:**
- [x] create_role() создает роль с правильными данными
- [x] create_role() выбрасывает RoleAlreadyExistsError при дублировании
- [x] get_role() возвращает роль по ID
- [x] get_role() возвращает None если роль не найдена
- [x] get_role_by_name() работает правильно
- [x] list_roles() возвращает все роли
- [x] update_role() обновляет display_name и description
- [x] delete_role() удаляет роль и cascade удаляет mappings
- [x] delete_role() выбрасывает SystemRoleCannotBeDeletedError для встроенных ролей

**Test Coverage:** ≥ 95%

---

#### 5.2 Unit Tests for UserRoleService
**Priority:** High  
**Effort:** 6-8 hours  
**Owner:** Backend Developer 1  

**Description:**
Написать unit tests для всех методов UserRoleService.

**Test Cases:**
- [x] assign_role() создает mapping для пользователя и роли
- [x] assign_role() выбрасывает UserNotFoundError если пользователя нет
- [x] assign_role() выбрасывает RoleNotFoundError если роли нет
- [x] assign_role() выбрасывает UserAlreadyHasRoleError при дублировании
- [x] remove_role() удаляет роль пользователя
- [x] get_user_roles() возвращает список имен ролей (без N+1 queries)
- [x] has_role() возвращает True если пользователь имеет роль
- [x] has_role() возвращает False если нет роли

---

#### 5.3 Integration Tests with TokenService
**Priority:** High  
**Effort:** 6-8 hours  
**Owner:** Backend Developer 2  

**Description:**
Написать интеграционные tests для TokenService с ролями.

**Test Cases:**
- [x] JWT payload содержит roles field
- [x] Roles в JWT соответствуют ролям в БД
- [x] Если пользователю нет ролей, JWT содержит role "user"
- [x] JWT валидируется правильно (signature и т.д.)
- [x] Backward compatibility (scope field сохранен)

---

#### 5.4 API Tests
**Priority:** High  
**Effort:** 8-12 hours  
**Owner:** Backend Developer 2  

**Description:**
Написать API tests для всех endpoints используя TestClient.

**Test Cases:**
- [x] POST /api/v1/admin/roles создает роль
- [x] GET /api/v1/admin/roles возвращает все роли
- [x] GET /api/v1/admin/roles/{id} возвращает конкретную роль
- [x] PUT /api/v1/admin/roles/{id} обновляет роль
- [x] DELETE /api/v1/admin/roles/{id} удаляет роль
- [x] POST /api/v1/admin/users/{uid}/roles добавляет роль
- [x] GET /api/v1/admin/users/{uid}/roles список ролей
- [x] DELETE /api/v1/admin/users/{uid}/roles/{name} удаляет роль
- [x] Все endpoints возвращают 401 без токена
- [x] Все endpoints возвращают 403 без admin scope
- [x] Error responses имеют правильный формат

---

#### 5.5 Database Tests
**Priority:** Medium  
**Effort:** 4-6 hours  
**Owner:** Backend Developer 1  

**Description:**
Написать tests для database migrations.

**Test Cases:**
- [x] roles table создается с правильной схемой
- [x] user_role_mappings table создается с foreign keys
- [x] Constraints работают (UNIQUE, CASCADE и т.д.)
- [x] Seed data вставляется правильно
- [x] Migration может быть откачена без ошибок
- [x] Индексы создаются

---

### 6. Documentation

#### 6.1 API Documentation
**Priority:** High  
**Effort:** 4-6 hours  
**Owner:** Backend Developer or Tech Writer  

**Description:**
Документировать все endpoints в OpenAPI/Swagger и в markdown.

**Deliverables:**
- [x] OpenAPI spec updated автоматически (FastAPI генерирует)
- [x] Swagger UI работает на /docs
- [x] Markdown документ с примерами curl commands
- [x] JSON examples request/response
- [x] Error codes документированы

---

#### 6.2 Code Documentation
**Priority:** High  
**Effort:** 3-4 hours  
**Owner:** Backend Developers  

**Description:**
Убедиться что все классы, методы и функции имеют docstrings на русском.

**Acceptance Criteria:**
- [x] Все классы имеют docstrings
- [x] Все методы имеют docstrings с Args, Returns, Raises
- [x] Все docstrings на русском языке
- [x] Примеры кода в docstrings где применимо

---

#### 6.3 Update docs/RBAC_SPECIFICATION.md
**Priority:** Medium  
**Effort:** 3-4 hours  
**Owner:** Tech Writer  

**Description:**
Обновить главный RBAC документ с ссылками на Phase 1 implementation.

**Deliverables:**
- [x] Добавить ссылки на openspec/changes/phase1/
- [x] Добавить примеры использования
- [x] Обновить timeline

---

### 7. Code Review & QA

#### 7.1 Code Review
**Priority:** High  
**Effort:** 4-6 hours  
**Owner:** Senior Developer  

**Description:**
Провести code review всего implementation.

**Checklist:**
- [x] Code style соответствует PEP 8
- [x] Type hints везде правильные
- [x] Нет obvious bugs или security issues
- [x] Performance приемлемая
- [x] Tests достаточны
- [x] Backward compatibility сохранена

---

#### 7.2 QA Testing
**Priority:** High  
**Effort:** 8-12 hours  
**Owner:** QA Engineer  

**Description:**
Провести manual и автоматизированное тестирование.

**Test Scenarios:**
- [x] Happy path: создать роль, назначить пользователю, получить JWT с ролью
- [x] Error scenarios: попытка дублирования, невалидные данные и т.д.
- [x] Performance: JWT generation < 100ms даже с 100+ ролей
- [x] Security: неавторизованный access отклоняется
- [x] Migration: upgrade и downgrade работают без потери данных

---

### 8. Deployment

#### 8.1 Prepare Deployment Plan
**Priority:** High  
**Effort:** 2-3 hours  
**Owner:** DevOps / Backend Lead  

**Description:**
Подготовить plan для deployment на production.

**Deliverables:**
- [x] Migration strategy (zero-downtime)
- [x] Rollback plan
- [x] Monitoring queries (для проверки что migration прошла OK)
- [x] Communication plan (for stakeholders)

---

#### 8.2 Deploy to Staging
**Priority:** High  
**Effort:** 2-4 hours  
**Owner:** DevOps  

**Description:**
Deploy Phase 1 на staging для финального тестирования.

**Acceptance Criteria:**
- [x] Код deployed на staging
- [x] Migrations прошли успешно
- [x] All tests проходят на staging
- [x] Эндпоинты работают
- [x] Логи чистые (нет ошибок)

---

#### 8.3 Deploy to Production
**Priority:** High  
**Effort:** 2-4 hours  
**Owner:** DevOps  

**Description:**
Deploy Phase 1 на production.

**Acceptance Criteria:**
- [x] Migrations прошли без ошибок
- [x] Zero downtime achieved
- [x] Seed data вставлен
- [x] All endpoints работают
- [x] Monitoring показывает нормальные метрики

---

## Dependency Graph

```
Database Schema & Migrations
    ├── 1.1 Create roles table
    ├── 1.2 Create user_role_mappings table
    └── 1.3 Seed initial roles
        ↓
Models Implementation
    ├── 2.1 Create Role model (requires: 1.1)
    ├── 2.2 Create UserRoleMapping model (requires: 1.2)
    └── 2.3 Update User model (requires: 1.1, 1.2)
        ↓
Services Implementation
    ├── 3.1 RoleService (requires: 2.1)
    ├── 3.2 UserRoleService (requires: 2.1, 2.2)
    └── 3.3 TokenService updates (requires: 3.2)
        ↓
API Endpoints
    ├── 4.1 Role Management endpoints (requires: 3.1)
    └── 4.2 User Role endpoints (requires: 3.2)
        ↓
Testing (parallel with implementation)
    ├── 5.1 RoleService tests
    ├── 5.2 UserRoleService tests
    ├── 5.3 TokenService integration tests
    ├── 5.4 API tests
    └── 5.5 Database tests
        ↓
Documentation & Review
    ├── 6.1 API documentation
    ├── 6.2 Code documentation
    ├── 6.3 Update RBAC_SPECIFICATION.md
    ├── 7.1 Code review
    └── 7.2 QA testing
        ↓
Deployment
    ├── 8.1 Prepare deployment plan
    ├── 8.2 Deploy to staging
    └── 8.3 Deploy to production
```

---

## Scheduling

### Week 1
- Task 1.1, 1.2, 1.3 (Database)
- Task 2.1, 2.2, 2.3 (Models)
- Task 3.1, 3.2 (RoleService, UserRoleService)

### Week 2
- Task 3.3 (TokenService)
- Task 4.1, 4.2 (API endpoints)
- Task 5.1, 5.2, 5.3, 5.4, 5.5 (Tests)

### Week 3
- Task 6.1, 6.2, 6.3 (Documentation)
- Task 7.1, 7.2 (Review & QA)
- Task 8.1, 8.2, 8.3 (Deployment)

---

## Notes

- Tasks 3.1 и 3.2 могут выполняться параллельно (разные сервисы)
- Tasks 4.1 и 4.2 могут выполняться параллельно
- Tests должны писаться одновременно с кодом (TDD approach)
- Code review должен быть after каждого набора tasks (не в конце)
- Все tasks должны быть приняты QA перед deployment

---

## Success Metrics

- ✅ Все tasks completed в schedule
- ✅ All tests passing (100% в CI/CD)
- ✅ Code coverage ≥ 85%
- ✅ Zero security issues в code review
- ✅ Performance metrics met (JWT < 100ms)
- ✅ Zero downtime deployment
- ✅ All stakeholders aligned
