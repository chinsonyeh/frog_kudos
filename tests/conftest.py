import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

def pytest_sessionfinish(session, exitstatus):
    """保證在所有 pytest 測試結束後，徹底清理測試夾具建立的暫存成員與隔離測試資料"""
    async def _cleanup():
        temp_engine = create_async_engine(settings.DATABASE_URL)
        async with temp_engine.begin() as conn:
            await conn.execute(text("DELETE FROM members WHERE name = '__TestParentRunner__';"))
            await conn.execute(text("DELETE FROM kudos_records WHERE member_id IN (SELECT id FROM members WHERE name LIKE 'ChildA_%' OR name LIKE 'ChildB_%' OR name LIKE 'Bot%');"))
            await conn.execute(text("DELETE FROM member_badges WHERE member_id IN (SELECT id FROM members WHERE name LIKE 'ChildA_%' OR name LIKE 'ChildB_%' OR name LIKE 'Bot%');"))
            await conn.execute(text("DELETE FROM redemptions WHERE member_id IN (SELECT id FROM members WHERE name LIKE 'ChildA_%' OR name LIKE 'ChildB_%' OR name LIKE 'Bot%');"))
            await conn.execute(text("DELETE FROM members WHERE name LIKE 'ChildA_%' OR name LIKE 'ChildB_%' OR name LIKE 'Bot%';"))
            await conn.execute(text("DELETE FROM redemptions WHERE item_id IN (SELECT id FROM reward_items WHERE title IN ('角色測試獎品', '小孩自選獎勵'));"))
            await conn.execute(text("DELETE FROM reward_items WHERE title IN ('角色測試獎品', '小孩自選獎勵');"))
        await temp_engine.dispose()
    try:
        asyncio.run(_cleanup())
        print("\n[conftest] cleanup succeeded!")
    except Exception as e:
        print(f"\n[conftest] cleanup error: {e}")
