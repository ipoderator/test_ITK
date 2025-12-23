from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from loguru import logger
from schemas import ItemCreate, ItemUpdate, ItemResponse
from database import ItemModel


async def get_all_items(db: AsyncSession) -> list[ItemResponse]:
    """Получить все элементы из базы данных"""
    try:
        logger.debug(
            "💾 [STORAGE] Выполнение SQL запроса: "
            "SELECT * FROM items ORDER BY id"
        )
        result = await db.execute(select(ItemModel).order_by(ItemModel.id))
        items = result.scalars().all()

        logger.debug(f"💾 [STORAGE] Получено {len(items)} записей из БД")

        items_list = [
            ItemResponse(
                id=item.id,
                name=item.name,
                description=item.description
            )
            for item in items
        ]
        logger.info(
            f"✅ [STORAGE] Успешно получено {len(items_list)} "
            f"элементов из базы данных"
        )
        return items_list
    except Exception as e:
        import traceback
        logger.error(
            f"❌ [STORAGE] Ошибка при получении всех элементов: {str(e)}"
        )
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


async def get_item_by_id(
    db: AsyncSession, item_id: int
) -> ItemResponse | None:
    """Получить элемент по ID из базы данных"""
    try:
        logger.debug(
            f"💾 [STORAGE] Выполнение SQL запроса: "
            f"SELECT * FROM items WHERE id = {item_id}"
        )
        result = await db.execute(
            select(ItemModel).where(ItemModel.id == item_id)
        )
        item = result.scalar_one_or_none()

        if item:
            desc = item.description if item.description else 'нет'
            logger.info(
                f"✅ [STORAGE] Элемент с ID {item_id} найден | "
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
                f"⚠️ [STORAGE] Элемент с ID {item_id} "
                f"не найден в базе данных"
            )
            return None
    except Exception as e:
        import traceback
        logger.error(
            f"❌ [STORAGE] Ошибка при получении элемента "
            f"по ID {item_id}: {str(e)}"
        )
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


async def create_item(db: AsyncSession, item: ItemCreate) -> ItemResponse:
    """Создать новый элемент в базе данных"""
    try:
        item_desc = item.description if item.description else 'нет'
        logger.debug(
            f"💾 [STORAGE] Создание нового элемента в БД | "
            f"name='{item.name}' | "
            f"description='{item_desc}'"
        )

        new_item_db = ItemModel(
            name=item.name,
            description=item.description
        )
        db.add(new_item_db)
        logger.debug(
            "💾 [STORAGE] Элемент добавлен в сессию, "
            "выполнение flush..."
        )
        await db.flush()
        await db.refresh(new_item_db)
        logger.debug(
            f"💾 [STORAGE] Элемент сохранен, "
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
            f"✅ [STORAGE] Новый элемент создан в БД | "
            f"ID={created_item.id} | "
            f"name='{created_item.name}' | "
            f"description='{created_desc}'"
        )
        return created_item
    except Exception as e:
        import traceback
        logger.error(
            f"❌ [STORAGE] Ошибка при создании элемента: {str(e)}"
        )
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


async def update_item(
    db: AsyncSession, item_id: int, item: ItemUpdate
) -> ItemResponse | None:
    """Обновить элемент в базе данных"""
    try:
        logger.debug(
            f"💾 [STORAGE] Поиск элемента ID={item_id} "
            f"для обновления..."
        )
        result = await db.execute(
            select(ItemModel).where(ItemModel.id == item_id)
        )
        existing_item_db = result.scalar_one_or_none()

        if existing_item_db is None:
            logger.warning(
                f"⚠️ [STORAGE] Попытка обновить несуществующий "
                f"элемент с ID {item_id}"
            )
            return None

        existing_desc = (
            existing_item_db.description
            if existing_item_db.description else 'нет'
        )
        logger.info(
            f"💾 [STORAGE] Элемент найден | "
            f"ID={item_id} | "
            f"Текущие данные: name='{existing_item_db.name}', "
            f"description='{existing_desc}'"
        )

        # Обновляем только переданные поля
        update_data = item.model_dump(exclude_unset=True)
        logger.debug(
            f"💾 [STORAGE] Обновление полей: "
            f"{list(update_data.keys())} | "
            f"Новые значения: {update_data}"
        )

        for field, value in update_data.items():
            old_value = getattr(existing_item_db, field)
            setattr(existing_item_db, field, value)
            logger.debug(
                f"💾 [STORAGE] Поле '{field}' обновлено: "
                f"'{old_value}' -> '{value}'"
            )

        logger.debug("💾 [STORAGE] Сохранение изменений в БД (flush)...")
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
            f"✅ [STORAGE] Элемент ID={item_id} обновлен | "
            f"Новые данные: name='{updated_item.name}', "
            f"description='{updated_desc}' | "
            f"Обновленные поля: {list(update_data.keys())}"
        )
        return updated_item
    except Exception as e:
        import traceback
        logger.error(
            f"❌ [STORAGE] Ошибка при обновлении элемента "
            f"ID {item_id}: {str(e)}"
        )
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


async def delete_item(db: AsyncSession, item_id: int) -> bool:
    """Удалить элемент из базы данных"""
    try:
        logger.debug(
            f"💾 [STORAGE] Поиск элемента ID={item_id} "
            f"для удаления..."
        )
        # Сначала получаем элемент для логирования
        result = await db.execute(
            select(ItemModel).where(ItemModel.id == item_id)
        )
        item_db = result.scalar_one_or_none()

        if item_db is None:
            logger.warning(
                f"⚠️ [STORAGE] Попытка удалить несуществующий "
                f"элемент с ID {item_id}"
            )
            return False

        item_name = item_db.name
        logger.info(
            f"💾 [STORAGE] Элемент найден для удаления | "
            f"ID={item_id} | name='{item_name}'"
        )

        # Удаляем элемент
        logger.debug(
            f"💾 [STORAGE] Выполнение SQL: "
            f"DELETE FROM items WHERE id = {item_id}"
        )
        await db.execute(
            delete(ItemModel).where(ItemModel.id == item_id)
        )
        await db.flush()
        logger.debug("💾 [STORAGE] Элемент удален из БД (flush выполнен)")

        logger.info(
            f"✅ [STORAGE] Элемент удален из базы данных | "
            f"ID={item_id} | name='{item_name}'"
        )
        return True
    except Exception as e:
        import traceback
        logger.error(
            f"❌ [STORAGE] Ошибка при удалении элемента ID {item_id}: {str(e)}"
        )
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise
