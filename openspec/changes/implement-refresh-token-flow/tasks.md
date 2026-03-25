# Задачи: Реализация Refresh Token Flow

## Фаза 1: Подготовка (База и схема)

### 1.1 Обновление модели RefreshToken
- [ ] Добавить колонки: `session_id`, `last_used`, `last_rotated_at`, `ip_address`, `user_agent`
- [ ] Обновить индексы в модели
- [ ] Добавить методы-помощники: `is_valid`, `is_expired`, `is_current`
- [ ] Написать unit тесты для модели

**Файлы:**
- `app/models/refresh_token.py`
- `tests/test_refresh_token_model.py`

**Оценка:** 2-3 часа

### 1.2 Создание миграции Alembic
- [ ] Создать файл миграции в `migration/versions/`
- [ ] Добавить upgrade() функцию для создания колонок и индексов
- [ ] Добавить downgrade() функцию
- [ ] Протестировать миграцию на развёртывание и откат
- [ ] Обновить БД в разработке

**Файлы:**
- `migration/versions/<timestamp>_add_session_management.py`

**Оценка:** 2 часа

## Фаза 2: Сервисы

### 2.1 Расширение RefreshTokenService
- [ ] Добавить метод `save_refresh_token()` с поддержкой session_id
- [ ] Расширить валидацию токенов (проверка reuse)
- [ ] Добавить метод `revoke_session()`
- [ ] Добавить метод `get_user_sessions()`
- [ ] Добавить метод `get_session_metadata()`
- [ ] Добавить логирование операций
- [ ] Написать unit тесты (>90% покрытие)

**Файлы:**
- `app/services/refresh_token_service.py`
- `tests/test_refresh_token_service.py`

**Оценка:** 4-5 часов

### 2.2 Создание SessionService
- [ ] Создать новый сервис `app/services/session_service.py`
- [ ] Метод `list_user_sessions(user_id)` - список активных сессий
- [ ] Метод `get_session_info(user_id, session_id)` - детали сессии
- [ ] Метод `revoke_session(user_id, session_id)` - отзыв сессии
- [ ] Метод `revoke_all_sessions(user_id, except_session_id)` - отзыв всех кроме
- [ ] Кэширование информации о сессиях
- [ ] Написать unit тесты

**Файлы:**
- `app/services/session_service.py`
- `tests/test_session_service.py`

**Оценка:** 3-4 часа

## Фаза 3: API Endpoints

### 3.1 Расширение OAuth endpoints
- [ ] Добавить session_id в _handle_password_grant() и _handle_refresh_grant()
- [ ] Улучшить обработку ошибок при переиспользовании токена
- [ ] Улучшить логирование операций
- [ ] Добавить capturing ip_address и user_agent
- [ ] Написать интеграционные тесты

**Файлы:**
- `app/api/v1/oauth.py`
- `tests/integration/test_oauth_flow.py`

**Оценка:** 3 часа

### 3.2 Создание Logout endpoint
- [ ] Создать endpoint `POST /api/v1/oauth/logout`
- [ ] Валидация access token
- [ ] Отзыв refresh token(ов)
- [ ] Опция all_sessions
- [ ] Обработка ошибок
- [ ] Логирование
- [ ] Написать интеграционные тесты

**Файлы:**
- `app/api/v1/oauth.py` (добавить функцию)
- `tests/integration/test_logout.py`

**Оценка:** 2-3 часа

### 3.3 Создание Session Management endpoints
- [ ] Создать router `app/api/v1/sessions.py`
- [ ] GET /sessions - список сессий
- [ ] GET /sessions/{id} - детали сессии
- [ ] DELETE /sessions/{id} - отзыв сессии
- [ ] DELETE /sessions?except_current=true - отзыв всех кроме текущей
- [ ] Авторизация и проверка владения
- [ ] Обработка ошибок
- [ ] Интеграционные тесты

**Файлы:**
- `app/api/v1/sessions.py` (новый файл)
- `app/main.py` (регистрация router)
- `tests/integration/test_sessions_api.py`

**Оценка:** 4-5 часов

## Фаза 4: Schemas и Models

### 4.1 Обновление OAuth schemas
- [ ] Расширить TokenResponse добавлением session_id
- [ ] Добавить LogoutRequest/LogoutResponse
- [ ] Добавить схемы ошибок
- [ ] Обновить документацию в docstrings

**Файлы:**
- `app/schemas/oauth.py`

**Оценка:** 1-2 часа

### 4.2 Создание Session schemas
- [ ] Создать SessionInfo DTO
- [ ] Создать ListSessionsResponse
- [ ] Создать GetSessionResponse
- [ ] Добавить валидацию

**Файлы:**
- `app/schemas/session.py` (новый файл)

**Оценка:** 1 час

## Фаза 5: Тестирование

### 5.1 Unit тесты
- [ ] Тесты RefreshTokenService (>90% покрытие)
- [ ] Тесты SessionService (>90% покрытие)
- [ ] Тесты models
- [ ] Тесты schemas

**Файлы:**
- `tests/test_refresh_token_service.py`
- `tests/test_session_service.py`
- `tests/test_refresh_token_model.py`
- `tests/test_session_schemas.py`

**Оценка:** 6-8 часов

### 5.2 Интеграционные тесты
- [ ] Полный refresh token flow (пароль grant → refresh grant → logout)
- [ ] Token reuse detection
- [ ] Session management (список, отзыв)
- [ ] Multi-session scenarios
- [ ] Error handling scenarios

**Файлы:**
- `tests/integration/test_refresh_token_flow.py`
- `tests/integration/test_session_management.py`
- `tests/integration/test_logout_flow.py`

**Оценка:** 8-10 часов

## Фаза 6: Документация и финализация

### 6.1 Документация API
- [ ] OpenAPI/Swagger аннотации для всех endpoints
- [ ] Примеры requests/responses
- [ ] Описание error codes

**Файлы:**
- `app/api/v1/oauth.py`
- `app/api/v1/sessions.py`

**Оценка:** 2 часа

### 6.2 Документация пользователя
- [ ] Создать `docs/REFRESH_TOKEN_GUIDE.md`
- [ ] Описать OAuth flow
- [ ] Описать token rotation
- [ ] Описать session management
- [ ] Security best practices
- [ ] Примеры использования

**Файлы:**
- `docs/REFRESH_TOKEN_GUIDE.md`

**Оценка:** 3 часа

### 6.3 Финальные проверки
- [ ] Прогон всех тестов
- [ ] Проверка покрытия кода (минимум 85%)
- [ ] Code review
- [ ] Integration testing в staging
- [ ] Performance testing

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
