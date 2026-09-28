import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

logger = logging.getLogger(__name__)

# 建立 SQLAlchemy 2.0 非同步資料庫連線引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)

# 非同步 Session 工廠
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

def log_safe_db_url():
    """安全輸出脫敏後的資料庫連線字串 (NFR-4)"""
    try:
        safe_url = engine.url.render_as_string(hide_password=True)
        logger.info(f"🐘 資料庫連線引擎已就緒: {safe_url}")
    except Exception as e:
        logger.warning(f"無法渲染脫敏資料庫 URL: {e}")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依賴注入：取得非同步資料庫 Session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
