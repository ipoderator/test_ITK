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
    """модель для таблицы items в postgresql"""
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)


# получаем url базы данных из переменной окружения
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://items_user:items_password@localhost:5432/items_db"
)


engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# создаем фабрику сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db() -> AsyncSession:
    """dependency для получения сессии бд"""
    logger.debug("[database] создание новой сессии базы данных...")
    async with AsyncSessionLocal() as session:
        try:
            yield session
            logger.debug("[database] коммит транзакции...")
            await session.commit()
            logger.debug("[database] транзакция успешно закоммичена")
        except Exception as e:
            logger.error(
                f"[database] ошибка в транзакции, выполнение rollback | "
                f"ошибка: {str(e)}"
            )
            await session.rollback()
            raise
        finally:
            logger.debug("[database] закрытие сессии базы данных")
            await session.close()


async def init_db():
    """инициализация базы данных - создание таблиц"""
    try:
        db_url_display = (
            DATABASE_URL.split('@')[1]
            if '@' in DATABASE_URL else 'скрыт'
        )
        logger.info(
            f"[database] инициализация базы данных | "
            f"URL: {db_url_display}"
        )
        logger.debug(
            "[database] проверка подключения к базе данных..."
        )
        async with engine.begin() as conn:
            logger.debug(
                "[database] создание таблиц "
                "(если не существуют)..."
            )
            await conn.run_sync(Base.metadata.create_all)
        logger.info(
            "[database] база данных инициализирована успешно | "
        )
    except Exception as e:
        import traceback
        logger.error(
            f"[database] критическая ошибка при инициализации бд | "
            f"ошибка: {str(e)}"
        )
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


async def close_db():
    """закрытие соединений с базой данных"""
    logger.info("[database] закрытие всех соединений с базой данных...")
    await engine.dispose()
    logger.info("[database] все соединения с базой данных успешно закрыты")
