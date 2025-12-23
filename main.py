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

# настройка логирования
logger.remove()
# логи в файл с детальной информацией
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
# логи в консоль для docker
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
    """управление жизненным циклом приложения"""
    logger.info("запуск приложения | инициализация сервиса...")
    try:
        logger.info("подключение к базе данных...")
        await init_db()
        logger.info("база данных успешно подключена и инициализирована")
    except Exception as e:
        import traceback
        logger.error(
            f"критическая ошибка подключения к бд | "
            f"ошибка: {str(e)}"
        )
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise
    logger.info(
        "приложение готово к работе | "
        "сервер запущен и готов принимать запросы"
    )
    yield
    logger.info("остановка приложения | начало процесса остановки...")
    await close_db()
    logger.info("приложение остановлено | все соединения закрыты")


app = FastAPI(
    title="items api",
    description="простое rest api для управления элементами (items)",
    version="1.0.0",
    lifespan=lifespan
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """middleware для логирования всех http запросов"""
    start_time = time.time()

    # получаем информацию о запросе
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    query_params = str(request.query_params) if request.query_params else "нет"

    logger.info(
        f"входящий запрос | "
        f"Method: {request.method} | "
        f"Path: {request.url.path} | "
        f"Query: {query_params} | "
        f"ip: {client_ip} | "
        f"User-Agent: {user_agent[:50]}"
    )

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # логируем размер ответа если возможно
        response_size = None
        if hasattr(response, 'body'):
            try:
                response_size = len(response.body) if response.body else 0
            except Exception:
                pass

        logger.info(
            f"ответ | "
            f"Method: {request.method} | "
            f"Path: {request.url.path} | "
            f"Status: {response.status_code} | "
            f"время обработки: {process_time:.4f}s | "
            f"размер ответа: "
            f"{response_size if response_size is not None else 'n/a'} bytes"
        )
        return response
    except Exception as e:
        process_time = time.time() - start_time
        import traceback
        error_traceback = traceback.format_exc()

        logger.error(
            f"ошибка при обработке запроса | "
            f"Method: {request.method} | "
            f"Path: {request.url.path} | "
            f"ip: {client_ip} | "
            f"ошибка: {str(e)} | "
            f"время до ошибки: {process_time:.4f}s"
        )
        logger.debug(f"Traceback: {error_traceback}")
        raise


@app.get(
    "/health",
    summary="проверка работоспособности api",
    description=(
        "проверяет, что api работает и доступно "
        "для обработки запросов"
    ),
    tags=["health"],
    responses={
        200: {
            "description": "API работает корректно",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "items api",
                        "version": "1.0.0"
                    }
                }
            }
        }
    }
)
async def health_check():
    """проверка работоспособности api"""
    logger.debug("health check запрос")
    return {
        "status": "healthy",
        "service": "items api",
        "version": "1.0.0"
    }


@app.get(
    "/health/db",
    summary="проверка подключения к базе данных",
    description="проверяет соединение с postgresql базой данных",
    tags=["health"],
    responses={
        200: {
            "description": "база данных доступна",
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
            "description": "база данных недоступна",
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
    """проверка подключения к базе данных"""
    logger.debug("health check запрос для базы данных")
    try:
        # выполняем простой запрос для проверки соединения
        await db.execute(text("select 1"))
        logger.debug("база данных доступна")
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"ошибка подключения к базе данных: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="database connection failed"
        )


@app.get(
    "/items",
    response_model=list[ItemResponse],
    summary="получить список элементов",
    description=(
        "возвращает список всех элементов с поддержкой "
        "пагинации и фильтрации по имени"
    ),
    responses={
        200: {
            "description": "успешный ответ со списком элементов",
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
                "максимальное количество элементов для возврата "
                "(от 1 до 100)"
            )
        )
    ] = 10,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description=(
                "смещение для пагинации "
                "(количество элементов для пропуска)"
            )
        )
    ] = 0,
    name: Annotated[
        str | None,
        Query(
            description=(
                "фильтр по имени элемента "
                "(частичное совпадение, регистронезависимый)"
            )
        )
    ] = None,
    db: AsyncSession = Depends(get_db)
) -> list[ItemResponse]:
    """получить список всех элементов с поддержкой пагинации и фильтрации"""
    logger.info(
        f"get /items | "
        f"параметры запроса: limit={limit}, offset={offset}, "
        f"name_filter='{name if name else 'не указан'}'"
    )

    logger.debug("начало получения элементов из базы данных...")
    items = await get_all_items(db)
    total_before_filter = len(items)
    logger.debug(f"получено {total_before_filter} элементов из бд")

    # применяем фильтрацию по имени, если указан и не пустой
    if name is not None and name.strip():
        logger.debug(f"применение фильтрации по имени: '{name}'")
        name_lower = name.lower()
        items = [item for item in items if name_lower in item.name.lower()]
        logger.info(
            f"фильтрация применена | "
            f"было элементов: {total_before_filter} | "
            f"стало после фильтрации: {len(items)} | "
            f"фильтр: '{name}'"
        )
    else:
        logger.debug("фильтрация по имени не применялась")

    # применяем пагинацию
    total_after_filter = len(items)
    logger.debug(f"применение пагинации: offset={offset}, limit={limit}")
    paginated_items = items[offset:offset + limit]

    logger.info(
        f"get /items - успешно | "
        f"возвращено элементов: {len(paginated_items)} | "
        f"всего после фильтрации: {total_after_filter} | "
        f"параметры пагинации: limit={limit}, offset={offset}"
    )

    return paginated_items


@app.get(
    "/items/{item_id}",
    response_model=ItemResponse,
    summary="получить элемент по id",
    description="возвращает один элемент по его уникальному идентификатору",
    responses={
        200: {
            "description": "успешный ответ с данными элемента",
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
            "description": "элемент с указанным id не найден",
            "content": {
                "application/json": {
                    "example": {"detail": "Item not found"}
                }
            }
        },
        422: {
            "description": (
                "некорректный id (должен быть положительным числом)"
            ),
            "content": {
                "application/json": {
                    "example": {"detail": "item id must be positive"}
                }
            }
        }
    }
)
async def get_item(
    item_id: Annotated[int, Path(ge=1)],
    db: AsyncSession = Depends(get_db)
) -> ItemResponse:
    """получить один элемент по id"""
    logger.info(f"get /items/{item_id} | запрос элемента по id: {item_id}")

    logger.debug(f"поиск элемента с id={item_id} в базе данных...")
    item = await get_item_by_id(db, item_id)

    if item is None:
        logger.warning(
            f"get /items/{item_id} | элемент не найден | "
            f"id: {item_id} | возврат 404"
        )
        raise HTTPException(status_code=404, detail="item not found")

    logger.info(
        f"get /items/{item_id} - успешно | "
        f"элемент найден: id={item.id}, name='{item.name}', "
        f"description='{item.description if item.description else 'нет'}'"
    )
    return item


@app.post(
    "/items",
    response_model=ItemResponse,
    status_code=201,
    summary="создать новый элемент",
    description="создает новый элемент с указанными данными",
    responses={
        201: {
            "description": "элемент успешно создан",
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
            "description": "некорректные данные запроса",
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
    """создать новый элемент"""
    description_str = (
        item.description if item.description is not None else 'нет описания'
    )
    logger.info(
        f"post /items | создание нового элемента | "
        f"name='{item.name}' | "
        f"description='{description_str}'"
    )

    try:
        logger.debug("сохранение элемента в базу данных...")
        created_item = await create_item(db, item)
        desc = created_item.description if created_item.description else 'нет'
        logger.info(
            f"post /items - успешно | "
            f"элемент создан: id={created_item.id} | "
            f"name='{created_item.name}' | "
            f"description='{desc}'"
        )
        return created_item
    except Exception as e:
        import traceback
        logger.error(
            f"post /items - ошибка при создании элемента | "
            f"name='{item.name}' | "
            f"ошибка: {str(e)}"
        )
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


@app.put(
    "/items/{item_id}",
    response_model=ItemResponse,
    summary="обновить элемент",
    description=(
        "обновляет существующий элемент по id. "
        "можно обновить только указанные поля"
    ),
    responses={
        200: {
            "description": "элемент успешно обновлен",
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
            "description": "элемент с указанным id не найден",
            "content": {
                "application/json": {
                    "example": {"detail": "Item not found"}
                }
            }
        },
        422: {
            "description": "некорректные данные запроса",
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
    """обновить существующий элемент"""
    update_data = item.model_dump(exclude_unset=True)
    update_fields = (
        list(update_data.keys()) if update_data else 'нет'
    )
    logger.info(
        f"put /items/{item_id} | обновление элемента | "
        f"id: {item_id} | "
        f"обновляемые поля: {update_fields} | "
        f"новые данные: {update_data}"
    )

    logger.debug(f"поиск элемента id={item_id} для обновления...")
    updated_item = await update_item(db, item_id, item)

    if updated_item is None:
        logger.warning(
            f"put /items/{item_id} | элемент не найден | "
            f"id: {item_id} | возврат 404"
        )
        raise HTTPException(status_code=404, detail="item not found")

    upd_desc = (
        updated_item.description
        if updated_item.description else 'нет'
    )
    logger.info(
        f"put /items/{item_id} - успешно обновлен | "
        f"id: {updated_item.id} | "
        f"name='{updated_item.name}' | "
        f"description='{upd_desc}'"
    )
    return updated_item


@app.delete(
    "/items/{item_id}",
    status_code=204,
    summary="удалить элемент",
    description="удаляет элемент по его уникальному идентификатору",
    responses={
        204: {
            "description": "элемент успешно удален"
        },
        404: {
            "description": "элемент с указанным id не найден",
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
            description="id элемента (должен быть положительным числом)"
        )
    ],
    db: AsyncSession = Depends(get_db)
) -> Response:
    """удалить элемент по id"""
    logger.info(
        f"delete /items/{item_id} | "
        f"запрос на удаление элемента | id: {item_id}"
    )

    logger.debug(f"поиск элемента id={item_id} для удаления...")
    if not await delete_item(db, item_id):
        logger.warning(
            f"delete /items/{item_id} | элемент не найден | "
            f"id: {item_id} | возврат 404"
        )
        raise HTTPException(status_code=404, detail="item not found")

    logger.info(
        f"delete /items/{item_id} - успешно удален | "
        f"элемент с id={item_id} удален из базы данных"
    )
    return Response(status_code=204)
