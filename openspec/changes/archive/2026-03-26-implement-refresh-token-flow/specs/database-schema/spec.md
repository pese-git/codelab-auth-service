# Спецификация: Обновление схемы БД

**Версия:** 1.0.0  
**Статус:** ✅ Обновленный компонент  
**Дата:** 2026-03-25

---

## 📋 Обзор

Обновление таблицы `refresh_tokens` для поддержки новых функциональностей:
- Управление сессиями (session_id)
- Отслеживание использования (last_used, last_rotated_at)
- Улучшенный аудит

## ADDED Requirements

### Requirement: Таблица сессий (sessions)

Система ДОЛЖНА хранить информацию об активных сессиях пользователя с поддержкой отзыва.

#### Scenario: Создание сессии
- **WHEN** пользователь получает новую пару токенов (access + refresh)
- **THEN** система создает запись в таблице sessions с session_id, user_id, client_id, created_at, expires_at

#### Scenario: Отзыв сессии
- **WHEN** пользователь выходит из системы
- **THEN** система отмечает сессию как отозванную (revoked=True, revoked_at=now)

## Текущая схема

```sql
CREATE TABLE refresh_tokens (
    id VARCHAR(36) PRIMARY KEY,
    jti_hash VARCHAR(64) NOT NULL UNIQUE,
    user_id VARCHAR(36) NOT NULL,
    client_id VARCHAR(255) NOT NULL,
    scope TEXT NOT NULL,
    expires_at DATETIME NOT NULL,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    revoked_at DATETIME,
    parent_jti_hash VARCHAR(64),
    created_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
    INDEX idx_jti_hash (jti_hash),
    INDEX idx_user_id (user_id),
    INDEX idx_expires_at (expires_at),
    INDEX idx_revoked (revoked)
)
```

## Новая схема (Миграция)

### Добавление новых колонок

```sql
ALTER TABLE refresh_tokens
ADD COLUMN session_id VARCHAR(36) NOT NULL DEFAULT (UUID()),
ADD COLUMN last_used DATETIME,
ADD COLUMN last_rotated_at DATETIME,
ADD COLUMN ip_address VARCHAR(45),
ADD COLUMN user_agent TEXT;
```

### Новые индексы

```sql
-- Индекс для быстрого поиска по session_id
CREATE INDEX idx_session_id ON refresh_tokens(session_id);

-- Индекс для быстрого поиска активных токенов пользователя
CREATE INDEX idx_user_active ON refresh_tokens(user_id, revoked);

-- Составной индекс для сессии
CREATE UNIQUE INDEX idx_user_client_session ON refresh_tokens(user_id, client_id, session_id);
```

### Полная новая схема

```sql
CREATE TABLE refresh_tokens (
    -- Первичный ключ
    id VARCHAR(36) PRIMARY KEY,
    
    -- Идентификация токена
    jti_hash VARCHAR(64) NOT NULL UNIQUE COMMENT 'SHA-256 hash JWT jti claim',
    
    -- Связи
    user_id VARCHAR(36) NOT NULL COMMENT 'User ID',
    client_id VARCHAR(255) NOT NULL COMMENT 'OAuth client ID',
    session_id VARCHAR(36) NOT NULL COMMENT 'Session identifier',
    
    -- Данные
    scope TEXT NOT NULL COMMENT 'Space-separated scopes',
    
    -- Сроки действия
    expires_at DATETIME NOT NULL COMMENT 'Token expiration',
    
    -- Отзыв
    revoked BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Revocation flag',
    revoked_at DATETIME COMMENT 'Revocation timestamp',
    
    -- Ротация
    parent_jti_hash VARCHAR(64) COMMENT 'Parent token hash for rotation chain',
    last_rotated_at DATETIME COMMENT 'Last rotation time',
    
    -- Использование
    last_used DATETIME COMMENT 'Last usage timestamp',
    
    -- Информация о клиенте
    ip_address VARCHAR(45) COMMENT 'Client IP address',
    user_agent TEXT COMMENT 'Client User-Agent',
    
    -- Временные метки
    created_at DATETIME NOT NULL COMMENT 'Creation timestamp',
    
    -- Внешние ключи
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
    
    -- Индексы
    INDEX idx_jti_hash (jti_hash),
    INDEX idx_user_id (user_id),
    INDEX idx_session_id (session_id),
    INDEX idx_expires_at (expires_at),
    INDEX idx_revoked (revoked),
    INDEX idx_user_active (user_id, revoked),
    UNIQUE INDEX idx_user_client_session (user_id, client_id, session_id)
)
```

## Миграция данных

### Скрипт миграции Alembic

```python
"""Add session management fields to refresh_tokens

Revision ID: <timestamp>_add_session_management
Revises: <previous_migration>
Create Date: 2026-03-25 14:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = '<timestamp>_add_session_management'
down_revision = '<previous_migration>'
branch_labels = None
depends_on = None

def upgrade():
    # Добавить новые колонки
    op.add_column('refresh_tokens', 
        sa.Column('session_id', sa.String(36), nullable=False, 
                  server_default=sa.func.uuid()))
    op.add_column('refresh_tokens', 
        sa.Column('last_used', sa.DateTime(timezone=True), nullable=True))
    op.add_column('refresh_tokens', 
        sa.Column('last_rotated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('refresh_tokens', 
        sa.Column('ip_address', sa.String(45), nullable=True))
    op.add_column('refresh_tokens', 
        sa.Column('user_agent', sa.Text, nullable=True))
    
    # Создать индексы
    op.create_index('idx_session_id', 'refresh_tokens', ['session_id'])
    op.create_index('idx_user_active', 'refresh_tokens', ['user_id', 'revoked'])
    op.create_index('idx_user_client_session', 'refresh_tokens', 
                   ['user_id', 'client_id', 'session_id'], unique=True)

def downgrade():
    # Удалить индексы
    op.drop_index('idx_user_client_session', table_name='refresh_tokens')
    op.drop_index('idx_user_active', table_name='refresh_tokens')
    op.drop_index('idx_session_id', table_name='refresh_tokens')
    
    # Удалить колонки
    op.drop_column('refresh_tokens', 'user_agent')
    op.drop_column('refresh_tokens', 'ip_address')
    op.drop_column('refresh_tokens', 'last_rotated_at')
    op.drop_column('refresh_tokens', 'last_used')
    op.drop_column('refresh_tokens', 'session_id')
```

## Обновление модели SQLAlchemy

### Файл: app/models/refresh_token.py

```python
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    # Первичный ключ
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    
    # Идентификация
    jti_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    
    # Связи
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), 
                                        nullable=False, index=True)
    client_id: Mapped[str] = mapped_column(String(255), ForeignKey("oauth_clients.client_id", 
                                                                   ondelete="CASCADE"), 
                                          nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    
    # Данные
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Истечение
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    # Отзыв
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Ротация
    parent_jti_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Использование
    last_used: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Информация о клиенте
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), 
                                                default=lambda: datetime.now(timezone.utc),
                                                nullable=False)
```

## Обратная совместимость

Изменения полностью обратно совместимы:
- Все новые колонки имеют NULL значения по умолчанию
- session_id генерируется автоматически для существующих записей
- Индексы улучшают производительность, но не обязательны для работы

## Performance Impact

- Новые индексы улучшают поиск сессий (O(1) вместо O(n))
- Рекомендуется запустить ANALYZE для оптимизации плана запросов
- Размер таблицы увеличится на ~50 bytes на запись (для новых колонок)

## Файлы реализации

- `migration/versions/<timestamp>_add_session_management.py` - миграция Alembic
- `app/models/refresh_token.py` - обновлённая модель

## Acceptance Criteria

- [ ] Миграция создана и протестирована
- [ ] Новые колонки добавлены
- [ ] Индексы созданы
- [ ] SQLAlchemy модель обновлена
- [ ] Обратная совместимость проверена
- [ ] Performance тесты пройдены
