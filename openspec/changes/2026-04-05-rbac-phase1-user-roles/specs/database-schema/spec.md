# Specification: Database Schema for RBAC Phase 1

**Версия:** 1.0.0  
**Дата:** 5 апреля 2026  
**Статус:** Specification  

---

## 1. Overview

Данная спецификация описывает полную SQL схему для поддержки пользовательских ролей в CodeLab Auth Service.

**Новые таблицы:**
- `roles` — каталог ролей в системе
- `user_role_mappings` — N:M связи между пользователями и ролями

---

## 2. Roles Table

### 2.1 SQL Definition

```sql
CREATE TABLE roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL UNIQUE,
  display_name VARCHAR(255),
  description TEXT,
  system_defined BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 Column Descriptions

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Уникальный идентификатор роли |
| `name` | VARCHAR(255) | NOT NULL, UNIQUE | Уникальное имя роли (admin, user, moderator) |
| `display_name` | VARCHAR(255) | NULLABLE | Отображаемое имя для UI (Admin, User, Moderator) |
| `description` | TEXT | NULLABLE | Подробное описание назначения роли |
| `system_defined` | BOOLEAN | DEFAULT FALSE | true для встроенных ролей, false для пользовательских |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Время создания записи |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Время последнего обновления |

### 2.3 Indices

```sql
-- Быстрый поиск по имени (часто используется в UserRoleService.get_role_by_name)
CREATE INDEX idx_roles_name ON roles(name);

-- Фильтрация встроенных ролей
CREATE INDEX idx_roles_system_defined ON roles(system_defined);
```

### 2.4 Constraints

```sql
-- UNIQUE constraint на name автоматически создается при определении колонки
ALTER TABLE roles ADD CONSTRAINT uc_roles_name UNIQUE (name);

-- PRIMARY KEY constraint
ALTER TABLE roles ADD CONSTRAINT pk_roles PRIMARY KEY (id);
```

### 2.5 Seed Data

```sql
INSERT INTO roles (id, name, display_name, description, system_defined, created_at, updated_at)
VALUES
  (gen_random_uuid(), 'admin', 'Administrator', 'Полный доступ ко всем функциям системы', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (gen_random_uuid(), 'moderator', 'Moderator', 'Модератор контента и управления пользователями', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  (gen_random_uuid(), 'user', 'User', 'Обычный пользователь с базовым доступом', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
```

---

## 3. User Role Mappings Table

### 3.1 SQL Definition

```sql
CREATE TABLE user_role_mappings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, role_id)
);
```

### 3.2 Column Descriptions

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `id` | UUID | PRIMARY KEY | Уникальный идентификатор связи |
| `user_id` | UUID | NOT NULL, FK(users.id), ON DELETE CASCADE | Ссылка на пользователя |
| `role_id` | UUID | NOT NULL, FK(roles.id), ON DELETE CASCADE | Ссылка на роль |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Время создания связи |

### 3.3 Foreign Keys

```sql
-- Ссылка на таблицу users
-- Если удалить пользователя, удалятся все его role mappings (CASCADE)
ALTER TABLE user_role_mappings
  ADD CONSTRAINT fk_user_role_mappings_user_id
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Ссылка на таблицу roles
-- Если удалить роль, удалятся все связи этой роли (CASCADE)
ALTER TABLE user_role_mappings
  ADD CONSTRAINT fk_user_role_mappings_role_id
  FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE;
```

### 3.4 Indices

```sql
-- Быстрый поиск ролей пользователя (в UserRoleService.get_user_roles)
CREATE INDEX idx_user_role_mappings_user_id ON user_role_mappings(user_id);

-- Быстрый поиск пользователей с конкретной ролью (для аудита и аналитики)
CREATE INDEX idx_user_role_mappings_role_id ON user_role_mappings(role_id);

-- Быстрый поиск конкретного user-role assignment
CREATE INDEX idx_user_role_mappings_user_role ON user_role_mappings(user_id, role_id);
```

### 3.5 Constraints

```sql
-- UNIQUE constraint — пользователь не может иметь одну роль дважды
ALTER TABLE user_role_mappings
  ADD CONSTRAINT uc_user_role_unique UNIQUE (user_id, role_id);
```

---

## 4. ER Diagram

```
┌─────────────────────────┐
│        USERS            │
├─────────────────────────┤
│ id (PK)                 │
│ email                   │
│ password_hash           │
│ email_verified          │
│ created_at              │
│ updated_at              │
└──────────┬──────────────┘
           │
           │ 1:N (через user_role_mappings)
           │
┌──────────▼──────────────────────────────┐
│    USER_ROLE_MAPPINGS                   │
├─────────────────────────────────────────┤
│ id (PK)                                 │
│ user_id (FK → users.id) [ON DELETE CASCADE] │
│ role_id (FK → roles.id) [ON DELETE CASCADE] │
│ created_at                              │
│ UNIQUE(user_id, role_id)                │
└──────────┬──────────────────────────────┘
           │
           │ N:1 (через role_id)
           │
┌──────────▼──────────────┐
│       ROLES             │
├─────────────────────────┤
│ id (PK)                 │
│ name (UNIQUE)           │
│ display_name            │
│ description             │
│ system_defined          │
│ created_at              │
│ updated_at              │
└─────────────────────────┘
```

---

## 5. Migration Strategy

### 5.1 Forward Migration (Upgrade)

```python
"""Create roles and user_role_mappings tables for RBAC Phase 1.

Revision ID: phase1_roles_initial
Revises: <previous_revision>
Create Date: 2026-04-05 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

def upgrade():
    # Создать таблицу roles
    op.create_table(
        'roles',
        sa.Column('id', UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('description', sa.String(1000), nullable=True),
        sa.Column('system_defined', sa.Boolean(), nullable=False, server_default=sa.literal(False)),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uc_roles_name')
    )
    
    # Создать индексы для roles
    op.create_index('idx_roles_name', 'roles', ['name'], unique=True)
    op.create_index('idx_roles_system_defined', 'roles', ['system_defined'])
    
    # Создать таблицу user_role_mappings
    op.create_table(
        'user_role_mappings',
        sa.Column('id', UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'role_id', name='uc_user_role_unique'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE')
    )
    
    # Создать индексы для user_role_mappings
    op.create_index('idx_user_role_mappings_user_id', 'user_role_mappings', ['user_id'])
    op.create_index('idx_user_role_mappings_role_id', 'user_role_mappings', ['role_id'])
    op.create_index('idx_user_role_mappings_user_role', 'user_role_mappings', ['user_id', 'role_id'])
    
    # Вставить seed data (встроенные роли)
    op.execute("""
        INSERT INTO roles (name, display_name, description, system_defined, created_at, updated_at)
        VALUES
            ('admin', 'Administrator', 'Полный доступ ко всем функциям системы', TRUE, NOW(), NOW()),
            ('moderator', 'Moderator', 'Модератор контента и управления пользователями', TRUE, NOW(), NOW()),
            ('user', 'User', 'Обычный пользователь с базовым доступом', TRUE, NOW(), NOW())
    """)

def downgrade():
    # Удалить таблицу user_role_mappings
    op.drop_table('user_role_mappings')
    
    # Удалить таблицу roles
    op.drop_table('roles')
```

### 5.2 Backward Migration (Downgrade)

Migration автоматически откатывается (downgrade function выше).

---

## 6. Query Examples

### 6.1 Получить все роли пользователя

```sql
SELECT r.id, r.name, r.display_name
FROM user_role_mappings urm
JOIN roles r ON urm.role_id = r.id
WHERE urm.user_id = 'user-id-here'
ORDER BY r.name;
```

**Performance:** O(1) with index on user_role_mappings.user_id

### 6.2 Проверить имеет ли пользователь конкретную роль

```sql
SELECT EXISTS (
  SELECT 1
  FROM user_role_mappings urm
  JOIN roles r ON urm.role_id = r.id
  WHERE urm.user_id = 'user-id-here' AND r.name = 'admin'
);
```

**Performance:** O(log n) with index

### 6.3 Получить всех пользователей с конкретной ролью

```sql
SELECT u.id, u.email
FROM users u
JOIN user_role_mappings urm ON u.id = urm.user_id
JOIN roles r ON urm.role_id = r.id
WHERE r.name = 'admin'
ORDER BY u.email;
```

**Performance:** O(log n) with index on role_id

### 6.4 Найти дублирующиеся role assignments

```sql
SELECT user_id, role_id, COUNT(*)
FROM user_role_mappings
GROUP BY user_id, role_id
HAVING COUNT(*) > 1;
```

**Result:** Должен быть пуст (UNIQUE constraint предотвращает дубли)

---

## 7. Data Integrity

### 7.1 Orphaned Records Prevention

**ON DELETE CASCADE** гарантирует:
- ✅ Если удалить пользователя → удалятся все его role mappings
- ✅ Если удалить роль → удалятся все user-role связи с этой ролью

```sql
-- Пример: удалить пользователя (автоматически удалятся его роли)
DELETE FROM users WHERE id = 'user-id-here';
-- user_role_mappings rows для этого user автоматически удалятся

-- Пример: удалить роль (автоматически удалятся все связи)
DELETE FROM roles WHERE name = 'moderator';
-- user_role_mappings rows для этой роли автоматически удалятся
```

### 7.2 UNIQUE Constraint

```sql
-- Невозможно добавить дубликат
INSERT INTO user_role_mappings (user_id, role_id)
VALUES ('user-id', 'role-id');
INSERT INTO user_role_mappings (user_id, role_id)
VALUES ('user-id', 'role-id'); -- Ошибка: UNIQUE constraint violation
```

---

## 8. Monitoring Queries

### 8.1 Проверить что миграция прошла успешно

```sql
-- Проверить таблицы существуют
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name IN ('roles', 'user_role_mappings');

-- Expected output:
-- roles
-- user_role_mappings

-- Проверить что seed data вставлен
SELECT COUNT(*) FROM roles WHERE system_defined = TRUE;
-- Expected: 3

-- Проверить что индексы созданы
SELECT indexname FROM pg_indexes 
WHERE tablename IN ('roles', 'user_role_mappings')
ORDER BY indexname;
```

### 8.2 Проверить дата целостность

```sql
-- Найти orphaned user_role_mappings (не должно быть)
SELECT urm.id
FROM user_role_mappings urm
WHERE urm.user_id NOT IN (SELECT id FROM users)
   OR urm.role_id NOT IN (SELECT id FROM roles);
-- Expected: empty result

-- Найти дубли (не должно быть)
SELECT user_id, role_id, COUNT(*)
FROM user_role_mappings
GROUP BY user_id, role_id
HAVING COUNT(*) > 1;
-- Expected: empty result
```

---

## 9. Backups & Disaster Recovery

### 9.1 Backup Strategy

```bash
# Перед миграцией создать backup
pg_dump codelab-auth-db > backup_before_phase1_$(date +%Y%m%d_%H%M%S).sql

# После успешной миграции (на staging)
pg_dump codelab-auth-db > backup_after_phase1_staging_$(date +%Y%m%d_%H%M%S).sql
```

### 9.2 Rollback Procedure

```bash
# Если что-то пошло не так, можно откатить миграцию
alembic downgrade -1

# Или полностью вернуть из backup
psql codelab-auth-db < backup_before_phase1_TIMESTAMP.sql
```

---

## 10. Performance Metrics

### 10.1 Expected Query Performance

| Query | Expected Time | Index Used |
|-------|--------|-----------|
| get_user_roles (single user) | < 10ms | idx_user_role_mappings_user_id |
| check_user_role (has_role) | < 5ms | idx_user_role_mappings_user_role |
| list_users_with_role | < 50ms | idx_user_role_mappings_role_id |
| create_role | < 5ms | None |
| assign_role | < 10ms | idx_user_role_mappings_user_id |

### 10.2 Storage Estimation

Для 100,000 users где каждый имеет среднее 2 роли:

```
roles table: ~3 rows × 500 bytes = 1.5 KB
user_role_mappings: 200,000 rows × 100 bytes = 20 MB
Total: ~20 MB (negligible)
```

---

## Acceptance Criteria

- [x] Таблица roles создана с правильной схемой
- [x] Таблица user_role_mappings создана с foreign keys
- [x] Все индексы созданы и работают
- [x] Seed data вставлен (3 встроенные роли)
- [x] UNIQUE constraints работают
- [x] CASCADE deletes работают
- [x] Миграция может быть откачена без ошибок
- [x] Queries работают с ожидаемой производительностью
- [x] Нет orphaned records
- [x] Backup/restore работает

---

## References

- SQL Standard: ISO/IEC 9075
- PostgreSQL Foreign Keys: https://www.postgresql.org/docs/current/ddl-constraints.html
- Alembic Documentation: https://alembic.sqlalchemy.org/
- Design: [`../design.md`](../design.md)
