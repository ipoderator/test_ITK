import os
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, Text
from loguru import logger


class Base(DeclarativeBase):
    pass


class ItemModel(Base):
    """Модель для таблицы items в PostgreSQL"""
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)


# Получаем URL базы данных из переменной окружения
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://items_user:items_password@localhost:5432/items_db"
)

# Создаем асинхронный движок SQLAlchemy
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Установите True для отладки SQL запросов
    pool_pre_ping=True,  # Проверка соединения перед использованием
    pool_size=10,
    max_overflow=20
)

# Создаем фабрику сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db() -> AsyncSession:
    """Dependency для получения сессии БД"""
    logger.debug("🔌 [DATABASE] Создание новой сессии базы данных...")
    async with AsyncSessionLocal() as session:
        try:
            yield session
            logger.debug("💾 [DATABASE] Коммит транзакции...")
            await session.commit()
            logger.debug("✅ [DATABASE] Транзакция успешно закоммичена")
        except Exception as e:
            logger.error(
                f"❌ [DATABASE] Ошибка в транзакции, выполнение rollback | "
                f"Ошибка: {str(e)}"
            )
            await session.rollback()
            raise
        finally:
            logger.debug("🔌 [DATABASE] Закрытие сессии базы данных")
            await session.close()


async def init_db():
    """Инициализация базы данных - создание таблиц"""
    try:
        db_url_display = (
            DATABASE_URL.split('@')[1]
            if '@' in DATABASE_URL else 'скрыт'
        )
        logger.info(
            f"🔌 [DATABASE] Инициализация базы данных | "
            f"URL: {db_url_display}"
        )
        logger.debug(
            "🔌 [DATABASE] Проверка подключения к базе данных..."
        )
        async with engine.begin() as conn:
            logger.debug(
                "🔌 [DATABASE] Создание таблиц "
                "(если не существуют)..."
            )
            await conn.run_sync(Base.metadata.create_all)
        logger.info(
            "✅ [DATABASE] База данных инициализирована успешно | "
            "Таблицы созданы/проверены"
        )
    except Exception as e:
        import traceback
        logger.error(
            f"❌ [DATABASE] Критическая ошибка при инициализации БД | "
            f"Ошибка: {str(e)}"
        )
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


async def close_db():
    """Закрытие соединений с базой данных"""
    logger.info("🔌 [DATABASE] Закрытие всех соединений с базой данных...")
    await engine.dispose()
    logger.info("✅ [DATABASE] Все соединения с базой данных успешно закрыты")
