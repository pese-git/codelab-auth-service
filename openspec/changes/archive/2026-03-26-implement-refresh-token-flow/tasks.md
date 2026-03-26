# Задачи: Реализация Refresh Token Flow

## Фаза 1: Подготовка (База и схема)

### 1.1 Обновление модели RefreshToken
- [x] Добавить колонки: `session_id`, `last_used`, `last_rotated_at`, `ip_address`, `user_agent`
- [x] Обновить индексы в модели
- [x] Добавить методы-помощники: `is_valid`, `is_expired`, `is_current`
- [x] Написать unit тесты для модели

**Файлы:**
- `app/models/refresh_token.py`
- `tests/test_refresh_token_model.py`

**Оценка:** 2-3 часа

### 1.2 Создание миграции Alembic
- [x] Создать файл миграции в `migration/versions/`
- [x] Добавить upgrade() функцию для создания колонок и индексов
- [x] Добавить downgrade() функцию
- [x] Протестировать миграцию на развёртывание и откат
- [x] Обновить БД в разработке

**Файлы:**
- `migration/versions/<timestamp>_add_session_management.py`

**Оценка:** 2 часа

## Фаза 2: Сервисы

### 2.1 Расширение RefreshTokenService
- [x] Добавить метод `save_refresh_token()` с поддержкой session_id
- [x] Расширить валидацию токенов (проверка reuse)
- [x] Добавить метод `revoke_session()`
- [x] Добавить метод `get_user_sessions()`
- [x] Добавить метод `get_session_metadata()`
- [x] Добавить логирование операций
- [x] Написать unit тесты (>90% покрытие)

**Файлы:**
- `app/services/refresh_token_service.py`
- `tests/test_refresh_token_service.py`

**Оценка:** 4-5 часов

### 2.2 Создание SessionService
- [x] Создать новый сервис `app/services/session_service.py`
- [x] Метод `list_user_sessions(user_id)` - список активных сессий
- [x] Метод `get_session_info(user_id, session_id)` - детали сессии
- [x] Метод `revoke_session(user_id, session_id)` - отзыв сессии
- [x] Метод `revoke_all_sessions(user_id, except_session_id)` - отзыв всех кроме
- [x] Кэширование информации о сессиях
- [x] Написать unit тесты

**Файлы:**
- `app/services/session_service.py`
- `tests/test_session_service.py`

**Оценка:** 3-4 часа

## Фаза 3: API Endpoints

### 3.1 Расширение OAuth endpoints
- [x] Добавить session_id в _handle_password_grant() и _handle_refresh_grant()
- [x] Улучшить обработку ошибок при переиспользовании токена
- [x] Улучшить логирование операций
- [x] Добавить capturing ip_address и user_agent
- [x] Написать интеграционные тесты

**Файлы:**
- `app/api/v1/oauth.py`
- `tests/integration/test_oauth_flow.py`

**Оценка:** 3 часа

### 3.2 Создание Logout endpoint
- [x] Создать endpoint `POST /api/v1/oauth/logout`
- [x] Валидация access token
- [x] Отзыв refresh token(ов)
- [x] Опция all_sessions
- [x] Обработка ошибок
- [x] Логирование
- [x] Написать интеграционные тесты

**Файлы:**
- `app/api/v1/oauth.py` (добавить функцию)
- `tests/integration/test_logout.py`

**Оценка:** 2-3 часа

### 3.3 Создание Session Management endpoints
- [x] Создать router `app/api/v1/sessions.py`
- [x] GET /sessions - список сессий
- [x] GET /sessions/{id} - детали сессии
- [x] DELETE /sessions/{id} - отзыв сессии
- [x] DELETE /sessions?except_current=true - отзыв всех кроме текущей
- [x] Авторизация и проверка владения
- [x] Обработка ошибок
- [x] Интеграционные тесты

**Файлы:**
- `app/api/v1/sessions.py` (новый файл)
- `app/main.py` (регистрация router)
- `tests/integration/test_sessions_api.py`

**Оценка:** 4-5 часов

## Фаза 4: Schemas и Models

### 4.1 Обновление OAuth schemas
- [x] Расширить TokenResponse добавлением session_id
- [x] Добавить LogoutRequest/LogoutResponse
- [x] Добавить схемы ошибок
- [x] Обновить документацию в docstrings

**Файлы:**
- `app/schemas/oauth.py`

**Оценка:** 1-2 часа

### 4.2 Создание Session schemas
- [x] Создать SessionInfo DTO
- [x] Создать ListSessionsResponse
- [x] Создать GetSessionResponse
- [x] Добавить валидацию

**Файлы:**
- `app/schemas/session.py` (новый файл)

**Оценка:** 1 час

## Фаза 5: Тестирование

### 5.1 Unit тесты
- [x] Тесты RefreshTokenService (>90% покрытие)
- [x] Тесты SessionService (>90% покрытие)
- [x] Тесты models
- [x] Тесты schemas

**Файлы:**
- `tests/test_refresh_token_service.py`
- `tests/test_session_service.py`
- `tests/test_refresh_token_model.py`
- `tests/test_session_schemas.py`

**Оценка:** 6-8 часов

### 5.2 Интеграционные тесты
- [x] Полный refresh token flow (пароль grant → refresh grant → logout)
- [x] Token reuse detection
- [x] Session management (список, отзыв)
- [x] Multi-session scenarios
- [x] Error handling scenarios

**Файлы:**
- `tests/integration/test_refresh_token_flow.py`
- `tests/integration/test_session_management.py`
- `tests/integration/test_logout_flow.py`

**Оценка:** 8-10 часов

## Фаза 6: Документация и финализация

### 6.1 Документация API
- [x] OpenAPI/Swagger аннотации для всех endpoints
- [x] Примеры requests/responses
- [x] Описание error codes

**Файлы:**
- `app/api/v1/oauth.py`
- `app/api/v1/sessions.py`

**Оценка:** 2 часа

### 6.2 Документация пользователя
- [x] Создать `docs/REFRESH_TOKEN_GUIDE.md`
- [x] Описать OAuth flow
- [x] Описать token rotation
- [x] Описать session management
- [x] Security best practices
- [x] Примеры использования

**Файлы:**
- `docs/REFRESH_TOKEN_GUIDE.md`

**Оценка:** 3 часа

### 6.3 Финальные проверки
- [x] Прогон всех тестов
- [x] Проверка покрытия кода (минимум 85%)
- [x] Code review
- [x] Integration testing в staging
- [x] Performance testing

**Оценка:** 4 часа

## Итого по фазам

| Фаза | Задачи | Время |
|------|--------|-------|
| 1 | Подготовка (модель, миграция) | 4-5 часов |
| 2 | Сервисы (RefreshToken, Session) | 7-9 часов |
| 3 | API Endpoints | 9-11 часов |
| 4 | Schemas | 2-3 часа |
| 5 | Тестирование | 14-18 часов |
| 6 | Документация | 9 часов |
| **Итого** | | **45-53 часа** |

## Зависимости между задачами

```
1.1 (модель) → 1.2 (миграция) → 2.1 (сервис) ↓
                                              ↓
                                      3.1 (OAuth endpoints)
                                              ↓
                                      3.2 (Logout)
                                              ↓
                                      3.3 (Sessions API)
                                      
4.1 (OAuth schemas) ↓
                    ↓→ 3.1 (OAuth endpoints)
4.2 (Session schemas) ↓
                      ↓→ 3.3 (Sessions API)

Все фазы 3 → 5 (Тестирование)
            ↓
            6 (Документация)
```

## Критерии приёмки

### Функциональность
- [x] Refresh token grant полностью реализован
- [x] Logout endpoint работает
- [x] Session management endpoints работают
- [x] Token reuse detection работает
- [x] Миграция БД успешно применяется

### Качество кода
- [x] Покрытие unit тестами > 90%
- [x] Все интеграционные тесты проходят
- [x] Нет критических issues в code review
- [x] Следование PEP 8 и project conventions

### Документация
- [x] OpenAPI документация полная
- [x] README/GUIDE документация есть
- [x] Примеры использования есть

### Security
- [x] Token reuse защита реализована
- [x] Авторизация проверяется
- [x] Audit logging реализован
- [x] SQL injection protection

### Performance
- [x] Индексы БД оптимизированы
- [x] Query performance приемлем
- [x] No N+1 queries
