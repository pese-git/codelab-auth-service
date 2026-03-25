# Proposal: Полноценная реализация механизма Refresh Token Flow

## Why

В текущей реализации сервиса аутентификации есть базовая инфраструктура для работы с refresh tokens (модель, сервис, OAuth endpoints), однако механизм неполностью реализован и требует:

1. **Завершения OAuth flow** - refresh token grant полностью интегрирован в `/token` endpoint, но нужна дополнительная логика для обработки edge cases
2. **Механизма revocation** - пользователи должны иметь возможность явно отозвать токены (logout)
3. **Токена ротации** - безопасная автоматическая ротация при каждом использовании
4. **Управления токенами** - endpoints для просмотра активных сессий и отзыва конкретных токенов
5. **Безопасности** - детектирование переиспользования токенов (token reuse detection)
6. **Документации и тестирования** - полное покрытие тестами и документация API

## What Changes

- **Завершение OAuth Token Endpoint** - добавление дополнительной валидации и улучшение обработки ошибок в `/api/v1/oauth/token`
- **Logout endpoint** - новый endpoint `POST /api/v1/oauth/logout` для отзыва текущего refresh token
- **Sessions management endpoints** - endpoints для просмотра активных сессий (`GET /api/v1/oauth/sessions`) и отзыва конкретной сессии (`DELETE /api/v1/oauth/sessions/{session_id}`)
- **Automatic token rotation** - улучшенная логика ротации токенов с отслеживанием цепи
- **Token reuse detection** - усиленная безопасность с автоматическим отзывом всей цепи при обнаружении переиспользования
- **Database schema enhancements** - миграция для дополнительных полей в таблице `refresh_tokens`
- **Comprehensive testing** - unit и интеграционные тесты для всех сценариев
- **API documentation** - полная документация endpoints в OpenAPI/Swagger

## Capabilities

### New Capabilities

- `refresh-token-oauth-flow`: Полная реализация OAuth 2.0 refresh token grant с валидацией, ротацией и детектированием переиспользования
- `token-revocation`: Механизм явного отзыва refresh tokens пользователем (logout)
- `session-management`: API endpoints для управления активными сессиями и отзыва конкретных токенов
- `token-rotation-security`: Автоматическая ротация токенов с отслеживанием цепи и защитой от replay атак
- `refresh-token-testing`: Comprehensive unit и интеграционные тесты для refresh token flow

### Modified Capabilities

- `user-authentication`: Расширение функционала аутентификации с полноценным refresh token flow
- `oauth-endpoints`: Улучшение `/token` endpoint с дополнительными проверками безопасности

## Impact

**Новые файлы:**
- `app/api/v1/sessions.py` - endpoints для управления сессиями
- `tests/test_refresh_token_flow.py` - интеграционные тесты refresh token flow
- `tests/test_session_management.py` - тесты endpoints управления сессиями
- `docs/REFRESH_TOKEN_GUIDE.md` - документация механизма refresh tokens

**Изменяемые файлы:**
- `app/models/refresh_token.py` - добавление поля `session_id` и других метаданных
- `app/services/refresh_token_service.py` - расширение функционала для ротации и управления сессиями
- `app/api/v1/oauth.py` - добавление logout и улучшение существующей логики
- `app/schemas/oauth.py` - добавление новых схем для endpoints
- `app/main.py` - регистрация новых routes
- `migration/versions/` - миграция для обновления схемы `refresh_tokens`

**Новые зависимости:** Нет

**Обновления БД:**
- Добавление колонок: `session_id` (STRING, unique per user/client combination), `last_rotated_at` (DATETIME)
- Индексы: на `session_id` и `user_id + client_id + revoked`

**API изменения:**
- Новые endpoints:
  - `POST /api/v1/oauth/logout` - отзыв текущего refresh token
  - `GET /api/v1/oauth/sessions` - просмотр активных сессий текущего пользователя
  - `DELETE /api/v1/oauth/sessions/{session_id}` - отзыв конкретной сессии
- Breaking changes: Нет, все изменения backward compatible

**Безопасность:**
- Детектирование переиспользования refresh tokens с автоматическим отзывом цепи
- Session-based token management для удобного управления несколькими устройствами
- Хеширование токенов в БД
- Rate-limiting на попытки использования рекомендуется на уровне API gateway
- Проверка header `X-Client-ID` для обеспечения привязки клиента
