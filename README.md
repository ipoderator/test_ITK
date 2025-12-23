# Items REST API

Простое REST API для управления элементами (Items) на FastAPI.

## Описание

Это простое REST API для работы с элементами. Позволяет создавать, читать, обновлять и удалять элементы через HTTP запросы.

Используемые технологии:
- FastAPI - фреймворк для создания API
- PostgreSQL - база данных
- Docker - для удобного запуска

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
- Параметры: `limit` (количество), `offset` (смещение), `name` (фильтр по имени)

**GET /items/{id}** - Получить элемент по ID

**POST /items** - Создать новый элемент
```json
{
  "name": "Название",
  "description": "Описание (необязательно)"
}
```

**PUT /items/{id}** - Обновить элемент
```json
{
  "name": "Новое название",
  "description": "Новое описание"
}
```

**DELETE /items/{id}** - Удалить элемент

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

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Запустите сервер:
```bash
uvicorn main:app --reload
```

3. Откройте в браузере: http://localhost:8000/docs

## Документация API

После запуска сервера документация доступна по адресу:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

В Swagger UI можно:
- Посмотреть все эндпоинты
- Протестировать API прямо в браузере
- Увидеть примеры запросов и ответов

## Тестирование через Postman

В папке `postman/` есть готовая коллекция для тестирования API.

1. Откройте Postman
2. Импортируйте файл `postman/Items_API.postman_collection.json`
3. Убедитесь, что `base_url` установлен в `http://localhost:8000`
4. Запустите тесты

## Примеры использования

### Создать элемент
```bash
curl -X POST "http://localhost:8000/items" \
  -H "Content-Type: application/json" \
  -d '{"name": "Тестовый элемент", "description": "Описание"}'
```

### Получить все элементы
```bash
curl "http://localhost:8000/items"
```

### Получить элемент по ID
```bash
curl "http://localhost:8000/items/1"
```

### Обновить элемент
```bash
curl -X PUT "http://localhost:8000/items/1" \
  -H "Content-Type: application/json" \
  -d '{"name": "Обновленное название"}'
```

### Удалить элемент
```bash
curl -X DELETE "http://localhost:8000/items/1"
```
