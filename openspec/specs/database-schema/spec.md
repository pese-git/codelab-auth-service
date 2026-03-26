# database-schema Specification

## Purpose
TBD - created by archiving change implement-refresh-token-flow. Update Purpose after archive.
## Requirements
### Requirement: Таблица сессий (sessions)

Система ДОЛЖНА хранить информацию об активных сессиях пользователя с поддержкой отзыва.

#### Scenario: Создание сессии
- **WHEN** пользователь получает новую пару токенов (access + refresh)
- **THEN** система создает запись в таблице sessions с session_id, user_id, client_id, created_at, expires_at

#### Scenario: Отзыв сессии
- **WHEN** пользователь выходит из системы
- **THEN** система отмечает сессию как отозванную (revoked=True, revoked_at=now)

