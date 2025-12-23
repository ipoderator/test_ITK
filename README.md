# Items REST API

Простое REST API для управления элементами (Items) на FastAPI.

## Описание

Это простое REST API для работы с элементами. Позволяет создавать, читать, обновлять и удалять элементы через HTTP запросы.

**Требования:**
- Python 3.11+
- PostgreSQL 15+
- Docker и Docker Compose 

**Используемые технологии:**
- FastAPI - фреймворк для создания API
- PostgreSQL - база данных
- Docker - для удобного запуска
- Loguru - для логирования

## Структура проекта

```
.
├── main.py              # Основной файл с API
├── schemas.py           # Схемы данных
├── storage.py           # Работа с базой данных
├── database.py          # Настройки базы данных
├── requirements.txt     # Зависимости
├── Dockerfile          # Docker образ
├── docker-compose.yml  # Docker Compose
└── postman/            # Postman коллекция для тестирования
```

## Эндпоинты API

### Health Check

**GET /health** - Проверка работы API

**GET /health/db** - Проверка подключения к базе данных

### CRUD операции

**GET /items** - Получить список всех элементов
- Параметры: `limit` (количество, по умолчанию 10, от 1 до 100), `offset` (смещение, по умолчанию 0), `name` (фильтр по имени, опционально)

**GET /items/{id}** - Получить элемент по ID

**POST /items** - Создать новый элемент

**PUT /items/{id}** - Обновить элемент

**DELETE /items/{id}** - Удалить элемент

## Примеры запросов и ответов

### GET /items - Получить список элементов

**Запрос:**
```bash
curl -X GET "http://localhost:8000/items?limit=10&offset=0&name=элемент"
```

**Ответ (200 OK):**
```json
[
  {
    "id": 1,
    "name": "Элемент 1",
    "description": "Описание элемента 1"
  },
  {
    "id": 2,
    "name": "Элемент 2",
    "description": "Описание элемента 2"
  }
]
```

**Примеры запросов:**
- Получить первые 10 элементов: `GET /items?limit=10&offset=0`
- Получить следующую страницу: `GET /items?limit=10&offset=10`
- Фильтрация по имени: `GET /items?name=тест`
- Комбинация параметров: `GET /items?limit=5&offset=0&name=элемент`

### GET /items/{id} - Получить элемент по ID

**Запрос:**
```bash
curl -X GET "http://localhost:8000/items/1"
```

**Ответ (200 OK):**
```json
{
  "id": 1,
  "name": "Элемент 1",
  "description": "Описание элемента 1"
}
```

**Ответ (404 Not Found):**
```json
{
  "detail": "item not found"
}
```

**Ответ (422 Unprocessable Entity):**
```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["path", "item_id"],
      "msg": "Input should be greater than or equal to 1",
      "input": 0
    }
  ]
}
```

### POST /items - Создать новый элемент

**Запрос:**
```bash
curl -X POST "http://localhost:8000/items" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Новый элемент",
    "description": "Описание нового элемента"
  }'
```

**Тело запроса:**
```json
{
  "name": "Новый элемент",
  "description": "Описание нового элемента"
}
```

**Ответ (201 Created):**
```json
{
  "id": 3,
  "name": "Новый элемент",
  "description": "Описание нового элемента"
}
```

**Ответ (422 Unprocessable Entity) - если поле name пустое:**
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "name"],
      "msg": "String should have at least 1 character",
      "input": ""
    }
  ]
}
```

**Ответ (422 Unprocessable Entity) - если поле name отсутствует:**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "name"],
      "msg": "Field required",
      "input": {"description": "Только описание"}
    }
  ]
}
```

### PUT /items/{id} - Обновить элемент

**Запрос (обновление всех полей):**
```bash
curl -X PUT "http://localhost:8000/items/1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Обновленное название",
    "description": "Обновленное описание"
  }'
```

**Тело запроса:**
```json
{
  "name": "Обновленное название",
  "description": "Обновленное описание"
}
```

**Ответ (200 OK):**
```json
{
  "id": 1,
  "name": "Обновленное название",
  "description": "Обновленное описание"
}
```

**Запрос (обновление только имени):**
```bash
curl -X PUT "http://localhost:8000/items/1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Только имя обновлено"
  }'
```

**Тело запроса:**
```json
{
  "name": "Только имя обновлено"
}
```

**Ответ (200 OK):**
```json
{
  "id": 1,
  "name": "Только имя обновлено",
  "description": "Обновленное описание"
}
```

**Ответ (404 Not Found):**
```json
{
  "detail": "item not found"
}
```

**Ответ (422 Unprocessable Entity) - если имя пустое:**
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "name"],
      "msg": "String should have at least 1 character",
      "input": ""
    }
  ]
}
```

### DELETE /items/{id} - Удалить элемент

**Запрос:**
```bash
curl -X DELETE "http://localhost:8000/items/1"
```

**Ответ (204 No Content):**
```
(пустое тело ответа)
```

**Ответ (404 Not Found):**
```json
{
  "detail": "item not found"
}
```

**Ответ (422 Unprocessable Entity) - если ID некорректный:**
```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["path", "item_id"],
      "msg": "Input should be greater than or equal to 1",
      "input": 0
    }
  ]
}
```

### GET /health - Проверка работоспособности API

**Запрос:**
```bash
curl -X GET "http://localhost:8000/health"
```

**Ответ (200 OK):**
```json
{
  "status": "healthy",
  "service": "items api",
  "version": "1.0.0"
}
```

### GET /health/db - Проверка подключения к базе данных

**Запрос:**
```bash
curl -X GET "http://localhost:8000/health/db"
```

**Ответ (200 OK):**
```json
{
  "status": "healthy",
  "database": "connected"
}
```

**Ответ (503 Service Unavailable):**
```json
{
  "detail": "database connection failed"
}
```

## Запуск проекта

### Вариант 1: Docker Compose (самый простой)

1. Клонируйте репозиторий:
```bash
git clone <URL_РЕПОЗИТОРИЯ>
cd ITK_academy
```

2. Запустите проект:
```bash
docker-compose up -d
```

3. Откройте в браузере: http://localhost:8000/docs

**Управление:**
- Логи: `docker-compose logs -f`
- Остановка: `docker-compose down`

### Вариант 2: Локальный запуск

**Требования:**
- Python 3.11 или выше
- PostgreSQL 15 или выше (должна быть запущена и доступна)

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Настройте переменные окружения (опционально):
```bash
export DATABASE_URL="postgresql+asyncpg://items_user:items_password@localhost:5432/items_db"
```

3. Запустите сервер:
```bash
uvicorn main:app --reload
```

4. Откройте в браузере: http://localhost:8000/docs

## Документация API

После запуска сервера документация доступна по адресу:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc


## Тестирование через Postman

В папке `postman/` есть готовая коллекция для тестирования API.

1. Откройте Postman
2. Импортируйте файл `postman/Items_API.postman_collection.json`
3. Убедитесь, что `base_url` установлен в `http://localhost:8000`
4. Запустите тесты
