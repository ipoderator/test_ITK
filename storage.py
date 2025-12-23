from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from loguru import logger
from schemas import ItemCreate, ItemUpdate, ItemResponse
from database import ItemModel


async def get_all_items(db: AsyncSession) -> list[ItemResponse]:
    """получить все элементы из базы данных"""
    try:
        logger.debug(
            "[storage] выполнение sql запроса: "
            "select * from items order by id"
        )
        result = await db.execute(select(ItemModel).order_by(ItemModel.id))
        items = result.scalars().all()

        logger.debug(f"[storage] получено {len(items)} записей из бд")

        items_list = [
            ItemResponse(
                id=item.id,
                name=item.name,
                description=item.description
            )
            for item in items
        ]
        logger.info(
            f"[storage] успешно получено {len(items_list)} "
            f"элементов из базы данных"
        )
        return items_list
    except Exception as e:
        import traceback
        logger.error(
            f"[storage] ошибка при получении всех элементов: {str(e)}"
        )
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


async def get_item_by_id(
    db: AsyncSession, item_id: int
) -> ItemResponse | None:
    """получить элемент по id из базы данных"""
    try:
        logger.debug(
            f"[storage] выполнение sql запроса: "
            f"select * from items where id = {item_id}"
        )
        result = await db.execute(
            select(ItemModel).where(ItemModel.id == item_id)
        )
        item = result.scalar_one_or_none()

        if item:
            desc = item.description if item.description else 'нет'
            logger.info(
                f"[storage] элемент с id {item_id} найден | "
                f"name='{item.name}' | "
                f"description='{desc}'"
            )
            return ItemResponse(
                id=item.id,
                name=item.name,
                description=item.description
            )
        else:
            logger.warning(
                f"[storage] элемент с id {item_id} "
                f"не найден в базе данных"
            )
            return None
    except Exception as e:
        import traceback
        logger.error(
            f"[storage] ошибка при получении элемента "
            f"по ID {item_id}: {str(e)}"
        )
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


async def create_item(db: AsyncSession, item: ItemCreate) -> ItemResponse:
    """создать новый элемент в базе данных"""
    try:
        item_desc = item.description if item.description else 'нет'
        logger.debug(
            f"[storage] создание нового элемента в бд | "
            f"name='{item.name}' | "
            f"description='{item_desc}'"
        )

        new_item_db = ItemModel(
            name=item.name,
            description=item.description
        )
        db.add(new_item_db)
        logger.debug(
            "[storage] элемент добавлен в сессию, "
            "выполнение flush..."
        )
        await db.flush()
        await db.refresh(new_item_db)
        logger.debug(
            f"[storage] элемент сохранен, "
            f"получен ID: {new_item_db.id}"
        )

        created_item = ItemResponse(
            id=new_item_db.id,
            name=new_item_db.name,
            description=new_item_db.description
        )

        created_desc = (
            created_item.description
            if created_item.description else 'нет'
        )
        logger.info(
            f"[storage] новый элемент создан в бд | "
            f"ID={created_item.id} | "
            f"name='{created_item.name}' | "
            f"description='{created_desc}'"
        )
        return created_item
    except Exception as e:
        import traceback
        logger.error(
            f"[storage] ошибка при создании элемента: {str(e)}"
        )
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


async def update_item(
    db: AsyncSession, item_id: int, item: ItemUpdate
) -> ItemResponse | None:
    """обновить элемент в базе данных"""
    try:
        logger.debug(
            f"[storage] поиск элемента id={item_id} "
            f"для обновления..."
        )
        result = await db.execute(
            select(ItemModel).where(ItemModel.id == item_id)
        )
        existing_item_db = result.scalar_one_or_none()

        if existing_item_db is None:
            logger.warning(
                f"[storage] попытка обновить несуществующий "
                f"элемент с ID {item_id}"
            )
            return None

        existing_desc = (
            existing_item_db.description
            if existing_item_db.description else 'нет'
        )
        logger.info(
            f"[storage] элемент найден | "
            f"ID={item_id} | "
            f"текущие данные: name='{existing_item_db.name}', "
            f"description='{existing_desc}'"
        )

        # обновляем только переданные поля
        update_data = item.model_dump(exclude_unset=True)
        logger.debug(
            f"[storage] обновление полей: "
            f"{list(update_data.keys())} | "
            f"новые значения: {update_data}"
        )

        for field, value in update_data.items():
            old_value = getattr(existing_item_db, field)
            setattr(existing_item_db, field, value)
            logger.debug(
                f"[storage] поле '{field}' обновлено: "
                f"'{old_value}' -> '{value}'"
            )

        logger.debug("[storage] сохранение изменений в бд (flush)...")
        await db.flush()
        await db.refresh(existing_item_db)

        updated_item = ItemResponse(
            id=existing_item_db.id,
            name=existing_item_db.name,
            description=existing_item_db.description
        )

        updated_desc = (
            updated_item.description
            if updated_item.description else 'нет'
        )
        logger.info(
            f"[storage] элемент id={item_id} обновлен | "
            f"новые данные: name='{updated_item.name}', "
            f"description='{updated_desc}' | "
            f"обновленные поля: {list(update_data.keys())}"
        )
        return updated_item
    except Exception as e:
        import traceback
        logger.error(
            f"[storage] ошибка при обновлении элемента "
            f"ID {item_id}: {str(e)}"
        )
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


async def delete_item(db: AsyncSession, item_id: int) -> bool:
    """удалить элемент из базы данных"""
    try:
        logger.debug(
            f"[storage] поиск элемента id={item_id} "
            f"для удаления..."
        )
        # сначала получаем элемент для логирования
        result = await db.execute(
            select(ItemModel).where(ItemModel.id == item_id)
        )
        item_db = result.scalar_one_or_none()

        if item_db is None:
            logger.warning(
                f"[storage] попытка удалить несуществующий "
                f"элемент с ID {item_id}"
            )
            return False

        item_name = item_db.name
        logger.info(
            f"[storage] элемент найден для удаления | "
            f"ID={item_id} | name='{item_name}'"
        )

        # удаляем элемент
        logger.debug(
            f"[storage] выполнение sql: "
            f"delete from items where id = {item_id}"
        )
        await db.execute(
            delete(ItemModel).where(ItemModel.id == item_id)
        )
        await db.flush()
        logger.debug("[storage] элемент удален из бд (flush выполнен)")

        logger.info(
            f"[storage] элемент удален из базы данных | "
            f"ID={item_id} | name='{item_name}'"
        )
        return True
    except Exception as e:
        import traceback
        logger.error(
            f"[storage] ошибка при удалении элемента id {item_id}: {str(e)}"
        )
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise
