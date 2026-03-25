# Спецификация моделей данных

**Версия:** 1.0.0  
**Статус:** ✅ Production Ready  
**Дата обновления:** 22 марта 2026

---

## 📊 Обзор модели данных

Система хранит данные в реляционной БД (SQLite для dev, PostgreSQL для prod). Модель включает таблицы для пользователей, OAuth клиентов, refresh токенов и логов аудита.

**Ключевые принципы:**
- ✅ Нормализованная схема (3NF)
- ✅ Индексы на часто используемые поля
- ✅ Foreign Keys для связей
- ✅ Хэширование чувствительных данных (пароли, токены)
- ✅ Временные метки для аудита
- ✅ Миграции через Alembic

---

## 🗂️ ER Диаграмма

```mermaid
erDiagram
    USERS ||--o{ REFRESH_TOKENS : creates
    USERS ||--o{ AUDIT_LOGS : generates
    USERS ||--o{ PASSWORD_RESET_TOKENS : generates
    OAUTH_CLIENTS ||--o{ REFRESH_TOKENS : issues
    OAUTH_CLIENTS ||--o{ AUDIT_LOGS : uses

    USERS {
        string id PK "UUID"
        string username UK "unique"
        string email UK "unique"
        string password_hash
        boolean is_active
        boolean is_verified
        timestamp created_at
        timestamp updated_at
        timestamp last_login_at
    }

    PASSWORD_RESET_TOKENS {
        string id PK "UUID"
        string user_id FK
        string token_hash UK "SHA-256"
        timestamp created_at
        timestamp expires_at
        timestamp used_at "nullable"
    }

    OAUTH_CLIENTS {
        string id PK "UUID"
        string client_id UK "unique"
        string client_secret_hash
        string name
        text description
        boolean is_confidential
        text allowed_scopes
        text allowed_grant_types
        integer access_token_lifetime
        integer refresh_token_lifetime
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    REFRESH_TOKENS {
        string id PK "UUID"
        string jti_hash UK "SHA-256"
        string user_id FK
        string client_id FK
        text scope
        timestamp expires_at
        boolean revoked
        timestamp revoked_at
        string parent_jti_hash
        timestamp created_at
    }

    AUDIT_LOGS {
        string id PK "UUID"
        string user_id FK "nullable"
        string client_id FK "nullable"
        string event_type
        json event_data
        string ip_address
        text user_agent
        boolean success
        text error_message
        timestamp created_at
    }
```

---

## 📋 Детальное описание таблиц

### 1. Таблица: users

**Назначение:** Хранение профилей пользователей системы

```sql
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP NULL,
    
    CONSTRAINT users_username_length CHECK (LENGTH(username) >= 3),
    CONSTRAINT users_username_max CHECK (LENGTH(username) <= 255)
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_is_active ON users(is_active);
```

**Поля:**

| Поле | Тип | Обязательно | Описание |
|------|-----|-----------|---------|
| `id` | UUID (VARCHAR 36) | ✅ | Уникальный идентификатор (v4 random) |
| `username` | VARCHAR(255) | ✅ | Имя пользователя, уникальное, 3+ символов |
| `email` | VARCHAR(255) | ✅ | Email адрес, уникальный, валидный формат |
| `password_hash` | VARCHAR(255) | ✅ | bcrypt хэш пароля (cost=12) |
| `is_active` | BOOLEAN | ✅ | Активен ли пользователь (для блокировки) |
| `is_verified` | BOOLEAN | ✅ | Верифицирован ли email |
| `created_at` | TIMESTAMP | ✅ | Дата создания профиля |
| `updated_at` | TIMESTAMP | ✅ | Дата последнего обновления |
| `last_login_at` | TIMESTAMP | ❌ | Дата последнего успешного входа |

**Индексы:**
- `email` — для быстрого поиска по email
- `username` — для быстрого поиска по username
- `is_active` — для фильтрации активных пользователей

**Пример данных:**
```sql
INSERT INTO users (id, username, email, password_hash, is_active, is_verified)
VALUES (
    '550e8400-e29b-41d4-a716-446655440000',
    'john.doe',
    'john@example.com',
    '$2b$12$...(bcrypt hash)...',
    TRUE,
    TRUE
);
```

---

### 2. Таблица: oauth_clients

**Назначение:** Регистрация OAuth2 клиентов (приложений)

```sql
CREATE TABLE oauth_clients (
    id VARCHAR(36) PRIMARY KEY,
    client_id VARCHAR(255) UNIQUE NOT NULL,
    client_secret_hash VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_confidential BOOLEAN DEFAULT FALSE,
    allowed_scopes TEXT NOT NULL,
    allowed_grant_types TEXT NOT NULL,
    access_token_lifetime INTEGER DEFAULT 900,
    refresh_token_lifetime INTEGER DEFAULT 2592000,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT oauth_clients_client_id_length 
        CHECK (LENGTH(client_id) >= 8)
);

CREATE INDEX idx_oauth_clients_client_id ON oauth_clients(client_id);
CREATE INDEX idx_oauth_clients_is_active ON oauth_clients(is_active);
```

**Поля:**

| Поле | Тип | Обязательно | Описание |
|------|-----|-----------|---------|
| `id` | UUID | ✅ | Уникальный идентификатор клиента |
| `client_id` | VARCHAR(255) | ✅ | Публичный идентификатор (используется в запросах) |
| `client_secret_hash` | VARCHAR(255) | ❌ | bcrypt хэш секрета (NULL для public клиентов) |
| `name` | VARCHAR(255) | ✅ | Название клиента (например, "CodeLab Flutter") |
| `description` | TEXT | ❌ | Описание клиента |
| `is_confidential` | BOOLEAN | ✅ | Тип клиента (true=confidential, false=public) |
| `allowed_scopes` | TEXT | ✅ | Разрешённые scopes (space-separated или JSON) |
| `allowed_grant_types` | TEXT | ✅ | Разрешённые grant types (JSON array) |
| `access_token_lifetime` | INTEGER | ✅ | Время жизни access token (секунды) |
| `refresh_token_lifetime` | INTEGER | ✅ | Время жизни refresh token (секунды) |
| `is_active` | BOOLEAN | ✅ | Активен ли клиент |
| `created_at` | TIMESTAMP | ✅ | Дата регистрации |
| `updated_at` | TIMESTAMP | ✅ | Дата последнего обновления |

**Seed данные:**
```sql
INSERT INTO oauth_clients 
(id, client_id, name, is_confidential, allowed_scopes, allowed_grant_types, is_active)
VALUES 
(
    '650e8400-e29b-41d4-a716-446655440001',
    'codelab-flutter-app',
    'CodeLab Flutter Application',
    FALSE,
    'api:read api:write',
    '["password", "refresh_token"]',
    TRUE
),
(
    '750e8400-e29b-41d4-a716-446655440002',
    'codelab-internal',
    'CodeLab Internal Services',
    TRUE,
    'api:admin api:internal',
    '["client_credentials"]',
    TRUE
);
```

---

### 3. Таблица: refresh_tokens

**Назначение:** Управление refresh токенами (одноразовые, с rotation)

```sql
CREATE TABLE refresh_tokens (
    id VARCHAR(36) PRIMARY KEY,
    jti_hash VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    client_id VARCHAR(255) NOT NULL,
    scope TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP,
    parent_jti_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
    
    CONSTRAINT refresh_tokens_expires_future 
        CHECK (expires_at > created_at)
);

CREATE INDEX idx_refresh_tokens_jti_hash ON refresh_tokens(jti_hash);
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);
CREATE INDEX idx_refresh_tokens_revoked ON refresh_tokens(revoked);
```

**Поля:**

| Поле | Тип | Обязательно | Описание |
|------|-----|-----------|---------|
| `id` | UUID | ✅ | Уникальный идентификатор записи |
| `jti_hash` | VARCHAR(64) | ✅ | SHA-256 хэш `jti` из JWT (для поиска) |
| `user_id` | VARCHAR(36) | ✅ | Ссылка на пользователя (Foreign Key) |
| `client_id` | VARCHAR(255) | ✅ | Ссылка на OAuth клиента (Foreign Key) |
| `scope` | TEXT | ✅ | Разрешения токена (space-separated) |
| `expires_at` | TIMESTAMP | ✅ | Дата истечения токена |
| `revoked` | BOOLEAN | ✅ | Отозван ли токен |
| `revoked_at` | TIMESTAMP | ❌ | Дата отзыва |
| `parent_jti_hash` | VARCHAR(64) | ❌ | SHA-256 хэш родительского refresh token (для ротации) |
| `created_at` | TIMESTAMP | ✅ | Дата создания |

**Логика rotation:**
```
Использование старого токена:
  1. Создать новый refresh token (jti_new)
  2. Сохранить: parent_jti_hash = jti_hash_старого
  3. Отозвать старый: revoked=TRUE
  4. При повторном использовании старого:
     - Обнаружить в истории (parent_jti_hash)
     - Отозвать всю цепочку (security incident)
     - Залогировать атаку
```

**Пример:**
```sql
INSERT INTO refresh_tokens 
(id, jti_hash, user_id, client_id, scope, expires_at)
VALUES (
    '850e8400-e29b-41d4-a716-446655440003',
    'a1b2c3d4e5f67890abcdef1234567890ab...',  -- SHA-256
    '550e8400-e29b-41d4-a716-446655440000',
    'codelab-flutter-app',
    'api:read api:write',
    DATETIME('now', '+30 days')
);
```

---

### 4. Таблица: password_reset_tokens

**Назначение:** Хранение криптографически защищённых одноразовых токенов для восстановления пароля

```sql
CREATE TABLE password_reset_tokens (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    token_hash VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP NULL,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    CONSTRAINT password_reset_tokens_expires_future 
        CHECK (expires_at > created_at)
);

CREATE INDEX idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);
CREATE INDEX idx_password_reset_tokens_token_hash ON password_reset_tokens(token_hash);
CREATE INDEX idx_password_reset_tokens_expires_at ON password_reset_tokens(expires_at);
```

**Поля:**

| Поле | Тип | Обязательно | Описание |
|------|-----|-----------|---------|
| `id` | UUID (VARCHAR 36) | ✅ | Уникальный идентификатор записи токена |
| `user_id` | VARCHAR(36) | ✅ | Ссылка на пользователя (Foreign Key) |
| `token_hash` | VARCHAR(64) | ✅ | SHA-256 хеш токена (для верификации, хранится в БД) |
| `created_at` | TIMESTAMP | ✅ | Дата и время создания токена |
| `expires_at` | TIMESTAMP | ✅ | Дата и время истечения (30 минут после создания) |
| `used_at` | TIMESTAMP | ❌ | Дата и время использования (NULL если не использован) |

**Индексы:**
- `user_id` — для быстрого поиска токенов пользователя
- `token_hash` — для верификации токена по хешу
- `expires_at` — для очистки истёкших токенов

**Логика использования:**
```
1. При запросе сброса пароля:
   - Генерируется токен: secrets.token_urlsafe(32)
   - Вычисляется хеш: SHA-256(token)
   - В БД сохраняется: id, user_id, token_hash, created_at, expires_at
   - Пользователю отправляется: полный token (не хеш!)

2. При подтверждении сброса:
   - Пользователь отправляет: token
   - Вычисляется хеш: SHA-256(token)
   - Поиск в БД: SELECT * FROM password_reset_tokens WHERE token_hash = ?
   - Проверка: expires_at > NOW() AND used_at IS NULL
   - При успехе: UPDATE password_reset_tokens SET used_at = NOW()

3. Очистка истёкших:
   - Периодически (cron) удалять записи где expires_at < NOW()
```

**Пример данных:**
```sql
INSERT INTO password_reset_tokens 
(id, user_id, token_hash, created_at, expires_at)
VALUES (
    '450e8400-e29b-41d4-a716-446655440005',
    '550e8400-e29b-41d4-a716-446655440000',
    'a1b2c3d4e5f67890abcdef1234567890ab...',  -- SHA-256
    CURRENT_TIMESTAMP,
    DATETIME('now', '+30 minutes')
);
```

---

### 5. Таблица: audit_logs

**Назначение:** Логирование всех операций аутентификации и авторизации

```sql
CREATE TABLE audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    client_id VARCHAR(255),
    event_type VARCHAR(50) NOT NULL,
    event_data JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_success ON audit_logs(success);
```

**Поля:**

| Поле | Тип | Обязательно | Описание |
|------|-----|-----------|---------|
| `id` | UUID | ✅ | Уникальный идентификатор лога |
| `user_id` | VARCHAR(36) | ❌ | Пользователь (NULL для неудачных входов) |
| `client_id` | VARCHAR(255) | ❌ | OAuth клиент |
| `event_type` | VARCHAR(50) | ✅ | Тип события (см. ниже) |
| `event_data` | JSON | ❌ | Доп. данные события (structured) |
| `ip_address` | VARCHAR(45) | ❌ | IP адрес клиента |
| `user_agent` | TEXT | ❌ | User-Agent браузера/приложения |
| `success` | BOOLEAN | ✅ | Успешна ли операция |
| `error_message` | TEXT | ❌ | Сообщение об ошибке (если есть) |
| `created_at` | TIMESTAMP | ✅ | Дата события |

**Event Types:**

| Event Type | Описание | Успех? | example event_data |
|-----------|---------|--------|-------------------|
| `login_success` | Успешный вход | ✅ | `{"username":"john","client_id":"flutter"}` |
| `login_failed` | Неудачный вход | ❌ | `{"reason":"invalid_password","attempts":3}` |
| `token_refresh` | Обновление токена | ✅ | `{"client_id":"flutter","scope":"api:read"}` |
| `token_revoke` | Отзыв токена | ✅ | `{"token_type":"refresh"}` |
| `token_reuse_detected` | Повторное использование | ❌ | `{"jti_hash":"...","parent_chain":[...]}` |
| `rate_limit_exceeded` | Rate limit | ❌ | `{"limit_type":"ip","limit":"5/min"}` |
| `brute_force_blocked` | Блокировка перебора | ❌ | `{"username":"john","attempts":5}` |
| `password_change` | Смена пароля | ✅ | `{"username":"john"}` |
| `password_reset_requested` | Запрос сброса пароля | ✅ | `{"email":"john@example.com","token_expires_in_minutes":30}` |
| `password_reset_confirmed` | Подтверждение сброса пароля | ✅ | `{"user_id":"..."}` |
| `password_reset_failed` | Ошибка при сбросе пароля | ❌ | `{"reason":"token_expired","email":"john@example.com"}` |
| `user_created` | Создание пользователя | ✅ | `{"username":"john","email":"john@..."}` |
| `user_blocked` | Блокировка пользователя | ✅ | `{"username":"john","reason":"..."}` |

**Пример:**
```sql
INSERT INTO audit_logs 
(id, user_id, client_id, event_type, event_data, ip_address, user_agent, success)
VALUES (
    '950e8400-e29b-41d4-a716-446655440004',
    '550e8400-e29b-41d4-a716-446655440000',
    'codelab-flutter-app',
    'login_success',
    '{"client_id":"codelab-flutter-app","scope":"api:read api:write"}',
    '192.168.1.100',
    'CodeLab/1.0.0 (Flutter; Android)',
    TRUE
);
```

---

## 🔑 Индексы и их назначение

### Primary Keys
- Автоматические индексы на `id` полях
- UUID для распределённости

### Foreign Keys
- `refresh_tokens.user_id` → `users.id`
- `refresh_tokens.client_id` → `oauth_clients.client_id`
- Cascade delete для целостности

### Search Indexes
- `users.email` — поиск пользователя по email
- `users.username` — поиск по username
- `oauth_clients.client_id` — поиск клиента
- `refresh_tokens.jti_hash` — поиск токена по JTI
- `refresh_tokens.user_id` — все токены пользователя

### Filter Indexes
- `users.is_active` — активные пользователи
- `oauth_clients.is_active` — активные клиенты
- `refresh_tokens.revoked` — отозванные токены
- `refresh_tokens.expires_at` — истекшие токены
- `audit_logs.success` — успешные/неудачные события

### Performance Indexes
```sql
-- Compound index для быстрого поиска активных токенов
CREATE INDEX idx_refresh_tokens_active 
ON refresh_tokens(user_id, revoked, expires_at);

-- Compound index для аудита
CREATE INDEX idx_audit_logs_user_event 
ON audit_logs(user_id, event_type, created_at);
```

---

## 🔐 Хэширование и безопасность

### Password Hashing

```python
# bcrypt с cost factor = 12
# Примерно 250ms на хэш (замедляет brute-force)
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Хэширование
hashed = pwd_context.hash("my_password")
# Результат: $2b$12$...

# Проверка (constant-time)
is_correct = pwd_context.verify("my_password", hashed)
```

### Token JTI Hashing

```python
import hashlib

# JWT содержит: jti = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
# В БД сохраняется хэш:
jti_hash = hashlib.sha256(jti.encode()).hexdigest()
# Результат: "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890"

# Благодаря хэшу:
# - Токен невозможно восстановить из БД
# - Быстрый поиск по хэшу (индекс)
```

---

## 📋 Миграции через Alembic

### Создание миграций

```bash
# Автогенерация миграции
alembic revision --autogenerate -m "Create users table"

# Применение всех миграций
alembic upgrade head

# Откат последней миграции
alembic downgrade -1

# Откат до конкретной версии
alembic downgrade ae1027a6acf
```

### Структура миграций

```
alembic/versions/
├── 001_initial_schema.py
├── 002_add_audit_logs.py
├── 003_add_indexes.py
└── 004_seed_oauth_clients.py
```

### Пример миграции

```python
# alembic/versions/001_initial_schema.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Создание таблиц
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('username', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_verified', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_login_at', sa.DateTime()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email'),
    )
    
    # Создание индексов
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_is_active', 'users', ['is_active'])

def downgrade():
    # Откат изменений
    op.drop_index('idx_users_is_active', 'users')
    op.drop_index('idx_users_username', 'users')
    op.drop_index('idx_users_email', 'users')
    op.drop_table('users')
```

---

## 🧹 Maintenance и Cleanup

### Очистка истекших токенов

```python
# Выполняется периодически (cron)
def cleanup_expired_refresh_tokens():
    """Удалить истекшие refresh tokens старше 7 дней"""
    cutoff_date = datetime.now() - timedelta(days=7)
    
    db.query(RefreshToken).filter(
        RefreshToken.expires_at < cutoff_date
    ).delete()
    
    db.commit()
```

**Рекомендуемое расписание:**
```cron
# Ежедневно в 2:00 ночи
0 2 * * * python cleanup_tokens.py
```

### Архивирование аудит логов

```python
def archive_old_audit_logs():
    """Архивировать логи старше 90 дней"""
    cutoff_date = datetime.now() - timedelta(days=90)
    
    # Экспортировать в файл
    old_logs = db.query(AuditLog).filter(
        AuditLog.created_at < cutoff_date
    ).all()
    
    # Сохранить в S3 или архив
    export_to_archive(old_logs)
    
    # Удалить из активной БД
    db.query(AuditLog).filter(
        AuditLog.created_at < cutoff_date
    ).delete()
```

---

## 📈 Стратегия миграции: SQLite → PostgreSQL

### Для Production развертывания

```bash
# 1. Экспортировать данные из SQLite
sqlite3 auth.db .dump > auth_dump.sql

# 2. Конвертировать SQL для PostgreSQL
pgloader sqlite:///auth.db postgresql://user:pass@host/auth_db

# 3. Или вручную:
# - Заменить типы данных (TEXT → UUID, etc.)
# - Переиндексировать
# - Проверить foreign keys

# 4. Обновить connection string
DATABASE_URL="postgresql://user:pass@host:5432/auth_db"

# 5. Применить миграции
alembic upgrade head

# 6. Проверить данные
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM refresh_tokens;
```

---

## 🔍 Примеры запросов

### Поиск пользователя

```python
# По username
user = db.query(User).filter(User.username == "john").first()

# По email
user = db.query(User).filter(User.email == "john@example.com").first()

# Активные пользователи
active_users = db.query(User).filter(User.is_active == True).all()
```

### Управление refresh tokens

```python
# Найти токен
token = db.query(RefreshToken).filter(
    RefreshToken.jti_hash == hashed_jti
).first()

# Все токены пользователя
user_tokens = db.query(RefreshToken).filter(
    RefreshToken.user_id == user_id,
    RefreshToken.revoked == False
).all()

# Истекшие токены
expired = db.query(RefreshToken).filter(
    RefreshToken.expires_at < datetime.now()
).all()

# Отозвать цепочку
db.query(RefreshToken).filter(
    RefreshToken.parent_jti_hash.in_(chain_hashes)
).update({"revoked": True})
```

### Аудит логирование

```python
# Все события пользователя
user_events = db.query(AuditLog).filter(
    AuditLog.user_id == user_id
).order_by(AuditLog.created_at.desc()).all()

# Неудачные попытки входа (последние 24 часа)
failed_logins = db.query(AuditLog).filter(
    AuditLog.event_type == "login_failed",
    AuditLog.created_at > datetime.now() - timedelta(hours=24)
).all()

# Обнаруженные атаки
security_incidents = db.query(AuditLog).filter(
    AuditLog.event_type == "token_reuse_detected"
).all()
```

---

## 📞 Контакты

**Разработчик:** Sergey Penkovsky  
**Email:** sergey.penkovsky@gmail.com  
**Версия:** 1.0.0  
**Дата:** 2026-03-22
