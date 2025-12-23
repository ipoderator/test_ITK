import time
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Path, Request, Depends
from fastapi.responses import Response
from typing import Annotated
from loguru import logger
from schemas import ItemCreate, ItemUpdate, ItemResponse
from storage import (
    get_all_items,
    get_item_by_id,
    create_item,
    update_item,
    delete_item
)
from database import get_db, init_db, close_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# Настройка логирования
logger.remove()
# Логи в файл с детальной информацией
logger.add(
    "logs/app_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    level="INFO",
    format=(
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
        "{name}:{function}:{line} - {message}"
    ),
    enqueue=True
)
# Логи в консоль для Docker
logger.add(
    sys.stderr,
    level="DEBUG",
    colorize=True,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    logger.info("🚀 ЗАПУСК ПРИЛОЖЕНИЯ | Инициализация сервиса...")
    try:
        logger.info("🔌 Подключение к базе данных...")
        await init_db()
        logger.info("✅ База данных успешно подключена и инициализирована")
    except Exception as e:
        import traceback
        logger.error(
            f"❌ КРИТИЧЕСКАЯ ОШИБКА ПОДКЛЮЧЕНИЯ К БД | "
            f"Ошибка: {str(e)}"
        )
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise
    logger.info(
        "✅ ПРИЛОЖЕНИЕ ГОТОВО К РАБОТЕ | "
        "Сервер запущен и готов принимать запросы"
    )
    yield
    logger.info("🛑 ОСТАНОВКА ПРИЛОЖЕНИЯ | Начало процесса остановки...")
    await close_db()
    logger.info("✅ ПРИЛОЖЕНИЕ ОСТАНОВЛЕНО | Все соединения закрыты")


app = FastAPI(
    title="Items API",
    description="Простое REST API для управления элементами (Items)",
    version="1.0.0",
    lifespan=lifespan
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware для логирования всех HTTP запросов"""
    start_time = time.time()

    # Получаем информацию о запросе
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    query_params = str(request.query_params) if request.query_params else "нет"

    logger.info(
        f"📥 ВХОДЯЩИЙ ЗАПРОС | "
        f"Method: {request.method} | "
        f"Path: {request.url.path} | "
        f"Query: {query_params} | "
        f"IP: {client_ip} | "
        f"User-Agent: {user_agent[:50]}"
    )

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Логируем размер ответа если возможно
        response_size = None
        if hasattr(response, 'body'):
            try:
                response_size = len(response.body) if response.body else 0
            except Exception:
                pass

        logger.info(
            f"📤 ОТВЕТ | "
            f"Method: {request.method} | "
            f"Path: {request.url.path} | "
            f"Status: {response.status_code} | "
            f"Время обработки: {process_time:.4f}s | "
            f"Размер ответа: "
            f"{response_size if response_size is not None else 'N/A'} bytes"
        )
        return response
    except Exception as e:
        process_time = time.time() - start_time
        import traceback
        error_traceback = traceback.format_exc()

        logger.error(
            f"❌ ОШИБКА ПРИ ОБРАБОТКЕ ЗАПРОСА | "
            f"Method: {request.method} | "
            f"Path: {request.url.path} | "
            f"IP: {client_ip} | "
            f"Ошибка: {str(e)} | "
            f"Время до ошибки: {process_time:.4f}s"
        )
        logger.debug(f"Traceback: {error_traceback}")
        raise


@app.get(
    "/health",
    summary="Проверка работоспособности API",
    description=(
        "Проверяет, что API работает и доступно "
        "для обработки запросов"
    ),
    tags=["Health"],
    responses={
        200: {
            "description": "API работает корректно",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "Items API",
                        "version": "1.0.0"
                    }
                }
            }
        }
    }
)
async def health_check():
    """Проверка работоспособности API"""
    logger.debug("🏥 Health check запрос")
    return {
        "status": "healthy",
        "service": "Items API",
        "version": "1.0.0"
    }


@app.get(
    "/health/db",
    summary="Проверка подключения к базе данных",
    description="Проверяет соединение с PostgreSQL базой данных",
    tags=["Health"],
    responses={
        200: {
            "description": "База данных доступна",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "database": "connected"
                    }
                }
            }
        },
        503: {
            "description": "База данных недоступна",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Database connection failed"
                    }
                }
            }
        }
    }
)
async def health_check_db(db: AsyncSession = Depends(get_db)):
    """Проверка подключения к базе данных"""
    logger.debug("🏥 Health check запрос для базы данных")
    try:
        # Выполняем простой запрос для проверки соединения
        await db.execute(text("SELECT 1"))
        logger.debug("✅ База данных доступна")
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к базе данных: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Database connection failed"
        )


@app.get(
    "/items",
    response_model=list[ItemResponse],
    summary="Получить список элементов",
    description=(
        "Возвращает список всех элементов с поддержкой "
        "пагинации и фильтрации по имени"
    ),
    responses={
        200: {
            "description": "Успешный ответ со списком элементов",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "name": "Item 1",
                            "description": "Description 1"
                        },
                        {
                            "id": 2,
                            "name": "Item 2",
                            "description": "Description 2"
                        }
                    ]
                }
            }
        }
    }
)
async def get_items(
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description=(
                "Максимальное количество элементов для возврата "
                "(от 1 до 100)"
            )
        )
    ] = 10,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description=(
                "Смещение для пагинации "
                "(количество элементов для пропуска)"
            )
        )
    ] = 0,
    name: Annotated[
        str | None,
        Query(
            description=(
                "Фильтр по имени элемента "
                "(частичное совпадение, регистронезависимый)"
            )
        )
    ] = None,
    db: AsyncSession = Depends(get_db)
) -> list[ItemResponse]:
    """Получить список всех элементов с поддержкой пагинации и фильтрации"""
    logger.info(
        f"🔍 GET /items | "
        f"Параметры запроса: limit={limit}, offset={offset}, "
        f"name_filter='{name if name else 'не указан'}'"
    )

    logger.debug("📊 Начало получения элементов из базы данных...")
    items = await get_all_items(db)
    total_before_filter = len(items)
    logger.debug(f"📊 Получено {total_before_filter} элементов из БД")

    # Применяем фильтрацию по имени, если указан и не пустой
    if name is not None and name.strip():
        logger.debug(f"🔎 Применение фильтрации по имени: '{name}'")
        name_lower = name.lower()
        items = [item for item in items if name_lower in item.name.lower()]
        logger.info(
            f"🔎 Фильтрация применена | "
            f"Было элементов: {total_before_filter} | "
            f"Стало после фильтрации: {len(items)} | "
            f"Фильтр: '{name}'"
        )
    else:
        logger.debug("🔎 Фильтрация по имени не применялась")

    # Применяем пагинацию
    total_after_filter = len(items)
    logger.debug(f"📄 Применение пагинации: offset={offset}, limit={limit}")
    paginated_items = items[offset:offset + limit]

    logger.info(
        f"✅ GET /items - УСПЕШНО | "
        f"Возвращено элементов: {len(paginated_items)} | "
        f"Всего после фильтрации: {total_after_filter} | "
        f"Параметры пагинации: limit={limit}, offset={offset}"
    )

    return paginated_items


@app.get(
    "/items/{item_id}",
    response_model=ItemResponse,
    summary="Получить элемент по ID",
    description="Возвращает один элемент по его уникальному идентификатору",
    responses={
        200: {
            "description": "Успешный ответ с данными элемента",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Item 1",
                        "description": "Description 1"
                    }
                }
            }
        },
        404: {
            "description": "Элемент с указанным ID не найден",
            "content": {
                "application/json": {
                    "example": {"detail": "Item not found"}
                }
            }
        },
        422: {
            "description": (
                "Некорректный ID (должен быть положительным числом)"
            ),
            "content": {
                "application/json": {
                    "example": {"detail": "Item ID must be positive"}
                }
            }
        }
    }
)
async def get_item(
    item_id: Annotated[int, Path(ge=1)],
    db: AsyncSession = Depends(get_db)
) -> ItemResponse:
    """Получить один элемент по ID"""
    logger.info(f"🔍 GET /items/{item_id} | Запрос элемента по ID: {item_id}")

    logger.debug(f"📊 Поиск элемента с ID={item_id} в базе данных...")
    item = await get_item_by_id(db, item_id)

    if item is None:
        logger.warning(
            f"⚠️ GET /items/{item_id} | ЭЛЕМЕНТ НЕ НАЙДЕН | "
            f"ID: {item_id} | Возврат 404"
        )
        raise HTTPException(status_code=404, detail="Item not found")

    logger.info(
        f"✅ GET /items/{item_id} - УСПЕШНО | "
        f"Элемент найден: ID={item.id}, name='{item.name}', "
        f"description='{item.description if item.description else 'нет'}'"
    )
    return item


@app.post(
    "/items",
    response_model=ItemResponse,
    status_code=201,
    summary="Создать новый элемент",
    description="Создает новый элемент с указанными данными",
    responses={
        201: {
            "description": "Элемент успешно создан",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "New Item",
                        "description": "New Description"
                    }
                }
            }
        },
        422: {
            "description": "Некорректные данные запроса",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "name"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def create_new_item(
    item: ItemCreate,
    db: AsyncSession = Depends(get_db)
) -> ItemResponse:
    """Создать новый элемент"""
    description_str = (
        item.description if item.description is not None else 'нет описания'
    )
    logger.info(
        f"➕ POST /items | Создание нового элемента | "
        f"name='{item.name}' | "
        f"description='{description_str}'"
    )

    try:
        logger.debug("💾 Сохранение элемента в базу данных...")
        created_item = await create_item(db, item)
        desc = created_item.description if created_item.description else 'нет'
        logger.info(
            f"✅ POST /items - УСПЕШНО | "
            f"Элемент создан: ID={created_item.id} | "
            f"name='{created_item.name}' | "
            f"description='{desc}'"
        )
        return created_item
    except Exception as e:
        import traceback
        logger.error(
            f"❌ POST /items - ОШИБКА ПРИ СОЗДАНИИ ЭЛЕМЕНТА | "
            f"name='{item.name}' | "
            f"Ошибка: {str(e)}"
        )
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


@app.put(
    "/items/{item_id}",
    response_model=ItemResponse,
    summary="Обновить элемент",
    description=(
        "Обновляет существующий элемент по ID. "
        "Можно обновить только указанные поля"
    ),
    responses={
        200: {
            "description": "Элемент успешно обновлен",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Updated Item",
                        "description": "Updated Description"
                    }
                }
            }
        },
        404: {
            "description": "Элемент с указанным ID не найден",
            "content": {
                "application/json": {
                    "example": {"detail": "Item not found"}
                }
            }
        },
        422: {
            "description": "Некорректные данные запроса",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "name"],
                                "msg": "string type expected",
                                "type": "type_error.str"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def update_existing_item(
    item_id: Annotated[int, Path(ge=1)],
    item: ItemUpdate,
    db: AsyncSession = Depends(get_db)
) -> ItemResponse:
    """Обновить существующий элемент"""
    update_data = item.model_dump(exclude_unset=True)
    update_fields = (
        list(update_data.keys()) if update_data else 'нет'
    )
    logger.info(
        f"✏️ PUT /items/{item_id} | Обновление элемента | "
        f"ID: {item_id} | "
        f"Обновляемые поля: {update_fields} | "
        f"Новые данные: {update_data}"
    )

    logger.debug(f"💾 Поиск элемента ID={item_id} для обновления...")
    updated_item = await update_item(db, item_id, item)

    if updated_item is None:
        logger.warning(
            f"⚠️ PUT /items/{item_id} | ЭЛЕМЕНТ НЕ НАЙДЕН | "
            f"ID: {item_id} | Возврат 404"
        )
        raise HTTPException(status_code=404, detail="Item not found")

    upd_desc = (
        updated_item.description
        if updated_item.description else 'нет'
    )
    logger.info(
        f"✅ PUT /items/{item_id} - УСПЕШНО ОБНОВЛЕН | "
        f"ID: {updated_item.id} | "
        f"name='{updated_item.name}' | "
        f"description='{upd_desc}'"
    )
    return updated_item


@app.delete(
    "/items/{item_id}",
    status_code=204,
    summary="Удалить элемент",
    description="Удаляет элемент по его уникальному идентификатору",
    responses={
        204: {
            "description": "Элемент успешно удален"
        },
        404: {
            "description": "Элемент с указанным ID не найден",
            "content": {
                "application/json": {
                    "example": {"detail": "Item not found"}
                }
            }
        }
    }
)
async def delete_existing_item(
    item_id: Annotated[
        int,
        Path(
            ge=1,
            description="ID элемента (должен быть положительным числом)"
        )
    ],
    db: AsyncSession = Depends(get_db)
) -> Response:
    """Удалить элемент по ID"""
    logger.info(
        f"🗑️ DELETE /items/{item_id} | "
        f"Запрос на удаление элемента | ID: {item_id}"
    )

    logger.debug(f"💾 Поиск элемента ID={item_id} для удаления...")
    if not await delete_item(db, item_id):
        logger.warning(
            f"⚠️ DELETE /items/{item_id} | ЭЛЕМЕНТ НЕ НАЙДЕН | "
            f"ID: {item_id} | Возврат 404"
        )
        raise HTTPException(status_code=404, detail="Item not found")

    logger.info(
        f"✅ DELETE /items/{item_id} - УСПЕШНО УДАЛЕН | "
        f"Элемент с ID={item_id} удален из базы данных"
    )
    return Response(status_code=204)
