# session-management Specification

## Purpose
TBD - created by archiving change implement-refresh-token-flow. Update Purpose after archive.
## Requirements
### Requirement: Список активных сессий

Система ДОЛЖНА предоставлять endpoint для просмотра всех активных сессий пользователя.

#### Scenario: Получение списка сессий
- **WHEN** аутентифицированный пользователь отправляет GET /api/v1/oauth/sessions
- **THEN** система возвращает JSON-массив со списком всех активных сессий с деталями (session_id, client_name, ip_address, last_used, is_current)

### Requirement: Отзыв сессии

Система ДОЛЖНА позволять пользователю отозвать конкретную сессию или все сессии.

#### Scenario: Отзыв конкретной сессии
- **WHEN** пользователь отправляет DELETE /api/v1/oauth/sessions/{session_id}
- **THEN** система отозывает все refresh токены для этой сессии и возвращает 200 OK

#### Scenario: Отзыв всех сессий
- **WHEN** пользователь отправляет POST /api/v1/oauth/logout с параметром all_sessions=true
- **THEN** система отозывает все refresh токены для всех сессий пользователя

