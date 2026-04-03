# token-revocation Specification

## Purpose
TBD - created by archiving change implement-refresh-token-flow. Update Purpose after archive.
## Requirements
### Requirement: Logout endpoint

Система ДОЛЖНА предоставлять endpoint для выхода пользователя из системы с отзывом токенов.

#### Scenario: Logout текущей сессии
- **WHEN** аутентифицированный пользователь отправляет POST /api/v1/auth/oauth/logout
- **THEN** система отозывает все refresh токены текущей сессии (revoked=True, revoked_at=now) и возвращает 200 OK с сообщением о успехе

#### Scenario: Logout всех сессий
- **WHEN** пользователь отправляет POST /api/v1/auth/oauth/logout с параметром all_sessions=true
- **THEN** система отозывает все refresh токены всех сессий пользователя и возвращает 200 OK

### Requirement: Детектирование атак переиспользования

Система ДОЛЖНА обнаруживать и предотвращать атаки переиспользования refresh tokens.

#### Scenario: Обнаружение попытки переиспользования
- **WHEN** клиент пытается использовать refresh token после того как он был отозван
- **THEN** система отозывает всю цепь токенов для этого пользователя/клиента и логирует SECURITY событие

