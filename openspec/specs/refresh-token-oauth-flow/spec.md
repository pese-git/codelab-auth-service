# refresh-token-oauth-flow Specification

## Purpose
TBD - created by archiving change implement-refresh-token-flow. Update Purpose after archive.
## Requirements
### Requirement: Реализация Refresh Token Grant Flow

Система ДОЛЖНА поддерживать RFC 6749 Section 6 refresh token grant для получения нового access token без повторной аутентификации.

#### Scenario: Успешное обновление токена
- **WHEN** клиент отправляет валидный refresh token на endpoint /api/v1/oauth/token с grant_type=refresh_token
- **THEN** система возвращает новую пару токенов (access_token, refresh_token) с 200 OK

#### Scenario: Детектирование переиспользования
- **WHEN** клиент пытается использовать refresh token дважды
- **THEN** система отозывает всю цепь токенов и возвращает ошибку invalid_grant с 401 Unauthorized

