# Email Templates Спецификация

**Версия:** 1.0.0  
**Статус:** ✅ New Capability  
**Дата:** 2026-03-23

---

## 📋 Обзор

Система шаблонов для отправки разных типов email с поддержкой динамического контента через шаблонизатор Jinja2. Включает шаблоны для приветствия, подтверждения email, сброса пароля и других уведомлений.

---

## ADDED Requirements

### Requirement: Система шаблонов с Jinja2

Система ДОЛЖНА предоставить механизм для создания и рендерирования email шаблонов с поддержкой динамических переменных через Jinja2.

#### Scenario: Рендеринг простого шаблона с переменными
- **WHEN** система рендерит шаблон "welcome.html" с переменными `{"username": "john", "email": "john@example.com"}`
- **THEN** возвращается HTML с подставленными значениями: "Привет, john" и "john@example.com"

#### Scenario: Рендеринг шаблона с условной логикой
- **WHEN** система рендерит шаблон с блоком {% if premium %}
- **THEN** блок отображается или скрывается в зависимости от значения переменной

#### Scenario: Рендеринг шаблона с циклами
- **WHEN** система рендерит шаблон с {% for item in items %}
- **THEN** блок повторяется для каждого элемента в списке

#### Scenario: Ошибка при рендеринге невалидного шаблона
- **WHEN** шаблон содержит синтаксическую ошибку Jinja2
- **THEN** система выбрасывает исключение с описанием ошибки

### Requirement: Коллекция встроенных шаблонов

Система ДОЛЖНА предоставить готовые HTML и текстовые шаблоны для основных типов email в приложении.

#### Scenario: Загрузка шаблона приветствия
- **WHEN** система загружает шаблон "welcome"
- **THEN** возвращается HTML шаблон с полями: {username}, {email}, {activation_link}

#### Scenario: Загрузка шаблона подтверждения email
- **WHEN** система загружает шаблон "confirmation"
- **THEN** возвращается HTML шаблон с полями: {username}, {confirmation_link}, {expires_at}

#### Scenario: Загрузка шаблона сброса пароля
- **WHEN** система загружает шаблон "password_reset"
- **THEN** возвращается HTML шаблон с полями: {username}, {reset_link}, {expires_at}

#### Scenario: Загрузка несуществующего шаблона
- **WHEN** система пытается загрузить шаблон с именем "nonexistent"
- **THEN** выбрасывается исключение TemplateNotFoundError

#### Scenario: Запрос списка доступных шаблонов
- **WHEN** система запрашивает список доступных шаблонов
- **THEN** возвращается список: ["welcome", "confirmation", "password_reset", ...]

### Requirement: Преобразование шаблона в email

Система ДОЛЖНА предоставить функцию преобразования рендереного шаблона в объект с заголовками и телом email.

#### Scenario: Создание email объекта из шаблона
- **WHEN** система преобразует рендереный шаблон в email
- **THEN** возвращается объект с атрибутами: subject, html_body, text_body, to, from

#### Scenario: Автоматическое создание текстовой версии из HTML
- **WHEN** шаблон содержит только HTML контент
- **THEN** система автоматически создает текстовую версию (stripping HTML tags)

#### Scenario: Email с кастомным subject
- **WHEN** шаблон задает кастомный subject в front-matter
- **THEN** email объект использует этот subject

### Requirement: Файловая структура шаблонов

Система ДОЛЖНА хранить шаблоны в стандартной директории структуре для удобства поддержки и развертывания.

#### Scenario: Директория шаблонов
- **WHEN** приложение инициализируется
- **THEN** существует директория `app/templates/emails/` с поддиректориями для каждого типа письма

#### Scenario: Структура файлов шаблонов
- **WHEN** система ищет шаблон "welcome"
- **THEN** загружаются файлы: `app/templates/emails/welcome/template.html` и `app/templates/emails/welcome/template.txt`

#### Scenario: Наследование базового шаблона
- **WHEN** шаблон использует {% extends "base.html" %}
- **THEN** контент наследует базовый layout с header, footer и styling

---

## Constraints

- **Jinja2 версия**: Использовать jinja2>=3.0.0
- **Безопасность**: Использовать autoescape=True для предотвращения XSS
- **Файлы**: Шаблоны должны быть текстовыми файлами (*.html, *.txt)
- **Кодировка**: Все файлы шаблонов должны быть в UTF-8
- **Именование**: Имена переменных в шаблонах должны быть snake_case
- **Размер**: HTML тело письма не должно превышать 100 KB
- **Синтаксис**: Не использовать JavaScript или вредоносный контент в шаблонах

---

## Dependencies

- **Зависит от**: `configuration` (путь к директории шаблонов может быть в конфиге)
- **Используется в**: `smtp-integration` (шаблоны рендерятся перед отправкой через SMTP)
- **Используется в**: `email-notifications` (система уведомлений использует шаблоны)

---

## Testing

### Unit Tests

1. **test_render_template_with_variables**
   - Рендеринг "welcome.html" с переменными
   - Проверить подстановку переменных в результат
   - Проверить валидный HTML в output

2. **test_render_template_with_conditions**
   - Шаблон с {% if condition %}
   - Проверить включение/исключение блока в зависимости от condition

3. **test_render_template_with_loops**
   - Шаблон с {% for item in items %}
   - Проверить повторение блока для каждого элемента

4. **test_jinja2_syntax_error**
   - Невалидный синтаксис в шаблоне
   - Проверить исключение с описанием ошибки

5. **test_get_available_templates**
   - Получить список доступных шаблонов
   - Проверить включение всех ожидаемых шаблонов

6. **test_template_not_found_error**
   - Запрос несуществующего шаблона
   - Проверить исключение TemplateNotFoundError

7. **test_create_email_from_template**
   - Преобразование шаблона в email объект
   - Проверить атрибуты subject, html_body, text_body, to, from

8. **test_autoescape_html**
   - Переменная содержит "<script>"
   - Проверить escaping в output для безопасности

9. **test_text_version_from_html**
   - HTML шаблон без текстовой версии
   - Проверить автоматическое создание текстовой версии

### Integration Tests

1. **test_load_builtin_templates**
   - Загрузить все встроенные шаблоны (welcome, confirmation, password_reset)
   - Проверить успешную загрузку каждого

2. **test_template_inheritance**
   - Шаблон наследует base.html
   - Проверить включение базового контента в результат

3. **test_template_with_special_characters**
   - Шаблон с кириллицей и спецсимволами
   - Проверить корректную обработку UTF-8

### Security Tests

1. **test_xss_prevention_in_template**
   - Переменная содержит потенциальный XSS (например, `<img src=x onerror=alert(1)>`)
   - Проверить что контент escapeн в HTML output

2. **test_template_injection_prevention**
   - Попытка инъекции в переменную (например, `{{ __import__('os').system('cmd') }}`)
   - Проверить что опасные функции недоступны в Jinja2

---

## Implementation Notes

- Использовать `jinja2.Environment` с `FileSystemLoader` для загрузки шаблонов
- Создать класс `EmailTemplateEngine` в `app/services/email_templates.py`
- Встроенные шаблоны хранить в `app/templates/emails/{template_name}/`
- Использовать `autoescape=True` для защиты от XSS
- Создать helper класс `EmailMessage` для представления готовых писем
- Логировать ошибки рендеринга для отладки
