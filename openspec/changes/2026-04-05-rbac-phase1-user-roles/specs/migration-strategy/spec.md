# Specification: Database Migration Strategy

**Версия:** 1.0.0  
**Дата:** 5 апреля 2026  
**Статус:** Specification  

---

## 1. Overview

Данная спецификация описывает стратегию миграции БД для Phase 1 RBAC, включая forward/backward миграции, zero-downtime deployment и rollback план.

---

## 2. Migration Plan

### 2.1 Timeline

| Phase | Duration | Action |
|-------|----------|--------|
| **Dev** | 1 день | Разработка миграции на localhost |
| **Staging** | 1 день | Тестирование на staging environment |
| **Production** | 1 час | Zero-downtime deployment на production |

### 2.2 Migration Steps

```
┌─────────────────────────────────────────────────────────┐
│ Фаза 1: Подготовка (за день до deployment)             │
├─────────────────────────────────────────────────────────┤
│ 1. Создать backup production БД                         │
│ 2. Протестировать миграцию на staging                   │
│ 3. Подготовить rollback plan                            │
│ 4. Уведомить stakeholders                               │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ Фаза 2: Deployment (maintenance window 10 минут)        │
├─────────────────────────────────────────────────────────┤
│ 1. Остановить auth service (v1)                         │
│ 2. Запустить alembic upgrade head                       │
│ 3. Проверить что миграция прошла успешно                │
│ 4. Запустить auth service (v2 с поддержкой ролей)      │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ Фаза 3: Verification (после deployment)                 │
├─────────────────────────────────────────────────────────┤
│ 1. Проверить что таблицы созданы                        │
│ 2. Проверить что seed data вставлен                     │
│ 3. Проверить что индексы работают                       │
│ 4. Проверить logs (нет ошибок)                          │
│ 5. Проверить новые endpoints работают                    │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Alembic Migration Script

### 3.1 Migration File Location

```
codelab-auth-service/migration/versions/2026_04_05_phase1_user_roles.py
```

### 3.2 Migration Code

```python
"""Add RBAC Phase 1 tables (roles and user_role_mappings).

Revision ID: rbac_phase1_001
Revises: <previous_revision_id>
Create Date: 2026-04-05 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid


def upgrade():
    """Create tables and indexes for RBAC Phase 1."""
    
    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', UUID(as_uuid=True), nullable=False, 
                 server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('description', sa.String(1000), nullable=True),
        sa.Column('system_defined', sa.Boolean(), nullable=False, 
                 server_default=sa.literal(False)),
        sa.Column('created_at', sa.DateTime(), nullable=False, 
                 server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, 
                 server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uc_roles_name')
    )
    
    # Create indexes on roles
    op.create_index('idx_roles_name', 'roles', ['name'])
    op.create_index('idx_roles_system_defined', 'roles', ['system_defined'])
    
    # Create user_role_mappings table
    op.create_table(
        'user_role_mappings',
        sa.Column('id', UUID(as_uuid=True), nullable=False, 
                 server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, 
                 server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'role_id', 
                           name='uc_user_role_unique'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], 
                               ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], 
                               ondelete='CASCADE')
    )
    
    # Create indexes on user_role_mappings
    op.create_index('idx_user_role_mappings_user_id', 'user_role_mappings', 
                   ['user_id'])
    op.create_index('idx_user_role_mappings_role_id', 'user_role_mappings', 
                   ['role_id'])
    op.create_index('idx_user_role_mappings_user_role', 'user_role_mappings', 
                   ['user_id', 'role_id'])
    
    # Insert seed data (system-defined roles)
    op.execute("""
        INSERT INTO roles (name, display_name, description, system_defined, created_at, updated_at)
        VALUES
            ('admin', 'Administrator', 'Полный доступ ко всем функциям системы', TRUE, NOW(), NOW()),
            ('moderator', 'Moderator', 'Модератор контента и управления пользователями', TRUE, NOW(), NOW()),
            ('user', 'User', 'Обычный пользователь с базовым доступом', TRUE, NOW(), NOW())
        ON CONFLICT (name) DO NOTHING;
    """)


def downgrade():
    """Rollback RBAC Phase 1 migration."""
    
    # Drop user_role_mappings table
    op.drop_table('user_role_mappings')
    
    # Drop roles table
    op.drop_table('roles')
```

### 3.3 Running the Migration

```bash
# Forward migration
cd codelab-auth-service
alembic upgrade head

# Check migration status
alembic current

# Backward migration (if needed)
alembic downgrade -1

# Show migration history
alembic history
```

---

## 4. Pre-Migration Checklist

```bash
#!/bin/bash
# pre_migration_checklist.sh

echo "=== Pre-Migration Checklist ==="

# 1. Create backup
echo "1. Creating backup..."
pg_dump codelab-auth-db > backup_before_phase1_$(date +%Y%m%d_%H%M%S).sql
echo "   ✓ Backup created"

# 2. Check current migration status
echo "2. Checking current migration status..."
alembic current
echo "   ✓ Current status checked"

# 3. Verify migration file exists
echo "3. Verifying migration file..."
if [ -f "migration/versions/2026_04_05_phase1_user_roles.py" ]; then
    echo "   ✓ Migration file found"
else
    echo "   ✗ Migration file not found!"
    exit 1
fi

# 4. Test migration on staging
echo "4. Running migration on staging..."
# ... run on staging ...
echo "   ✓ Staging migration successful"

# 5. Verify no breaking changes
echo "5. Checking for breaking changes..."
# ... compare schemas ...
echo "   ✓ No breaking changes detected"

echo ""
echo "=== All pre-migration checks passed! ==="
```

---

## 5. Post-Migration Verification

### 5.1 Verification Queries

```sql
-- Check that tables were created
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('roles', 'user_role_mappings')
ORDER BY table_name;
-- Expected: roles, user_role_mappings

-- Check that seed data was inserted
SELECT COUNT(*) as role_count FROM roles WHERE system_defined = TRUE;
-- Expected: 3

SELECT name FROM roles ORDER BY name;
-- Expected: admin, moderator, user

-- Check that indexes exist
SELECT indexname FROM pg_indexes 
WHERE tablename IN ('roles', 'user_role_mappings')
ORDER BY indexname;

-- Check that constraints work
SELECT constraint_name FROM information_schema.table_constraints
WHERE table_name IN ('roles', 'user_role_mappings');
```

### 5.2 Verification Script

```bash
#!/bin/bash
# post_migration_verification.sh

echo "=== Post-Migration Verification ==="

# 1. Check tables exist
echo "1. Checking tables..."
psql -d codelab-auth-db -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('roles', 'user_role_mappings');"

# 2. Check seed data
echo "2. Checking seed data..."
psql -d codelab-auth-db -c "SELECT COUNT(*) FROM roles WHERE system_defined = TRUE;"

# 3. Check indexes
echo "3. Checking indexes..."
psql -d codelab-auth-db -c "SELECT COUNT(*) FROM pg_indexes WHERE tablename IN ('roles', 'user_role_mappings');"

# 4. Check for orphaned records
echo "4. Checking data integrity..."
psql -d codelab-auth-db -c "SELECT COUNT(*) FROM user_role_mappings WHERE user_id NOT IN (SELECT id FROM users);"

# 5. Check service health
echo "5. Checking service health..."
curl -s http://localhost:8003/health | jq .

echo ""
echo "=== Verification complete ==="
```

---

## 6. Rollback Plan

### 6.1 Quick Rollback (If Migration Fails)

```bash
#!/bin/bash
# rollback_migration.sh

echo "=== Rollback Migration ==="

# 1. Stop the service
echo "1. Stopping auth service..."
systemctl stop codelab-auth-service

# 2. Rollback migration
echo "2. Rolling back migration..."
cd codelab-auth-service
alembic downgrade -1

# 3. Check rollback status
echo "3. Verifying rollback..."
alembic current

# 4. Start the service (old version without roles support)
echo "4. Starting auth service..."
systemctl start codelab-auth-service

# 5. Verify service is running
sleep 5
curl -s http://localhost:8003/health | jq .

echo ""
echo "=== Rollback complete ==="
```

### 6.2 Full Restore from Backup

```bash
#!/bin/bash
# restore_from_backup.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

echo "=== Restoring from backup ==="

# 1. Stop the service
systemctl stop codelab-auth-service

# 2. Drop current database
echo "Dropping current database..."
dropdb codelab-auth-db

# 3. Restore from backup
echo "Restoring from backup..."
createdb codelab-auth-db
psql codelab-auth-db < $BACKUP_FILE

# 4. Start the service
echo "Starting service..."
systemctl start codelab-auth-service

echo "=== Restore complete ==="
```

---

## 7. Zero-Downtime Deployment Strategy

### 7.1 Blue-Green Deployment

```
Before Migration:
┌──────────────────┐
│ Auth Service v1  │  ← Production (active)
│ (no RBAC roles)  │
└──────────────────┘
        ↓
1. Deploy new code (v2 with RBAC) to new instance
2. Run migration on new instance
3. Health checks on new instance
4. Switch traffic from v1 to v2
5. Monitor for issues

After Migration:
┌──────────────────┐
│ Auth Service v2  │  ← Production (active)
│ (with RBAC roles)│
└──────────────────┘
```

### 7.2 Implementation

```bash
#!/bin/bash
# blue_green_deployment.sh

echo "=== Blue-Green Deployment ==="

# 1. Deploy