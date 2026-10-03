import uuid
import bcrypt
from typing import Optional
from fastapi import HTTPException, Header, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings

def hash_pin(plain_pin: str) -> str:
    """使用 bcrypt 生成 PIN 碼之加鹽單向雜湊值"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_pin.strip().encode("utf-8"), salt).decode("utf-8")

def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    """驗證輸入之 PIN 碼與資料庫中的 bcrypt 雜湊是否相符"""
    if not plain_pin or not hashed_pin:
        return False
    try:
        return bcrypt.checkpw(
            plain_pin.strip().encode("utf-8"),
            hashed_pin.strip().encode("utf-8")
        )
    except Exception:
        return False

async def validate_parent_pin(
    db: AsyncSession,
    input_pin: Optional[str] = None,
    header_pin: Optional[str] = None
) -> bool:
    """
    家長 PIN 碼分級驗證機制 (Section 2.2 / Section 8):
    1. 支援從 JSON 欄位 input_pin 或 HTTP Header X-Parent-PIN 取值
    2. 比對所有 role='parent' 且 is_active=TRUE 的家長成員之 pin_code
    3. 若系統尚無任何有效家長 (冷啟動) 或家長尚未自訂 PIN，自動降級比對 .env 的 PARENT_DEFAULT_PIN
    """
    pin = (input_pin or header_pin or "").strip()
    if not pin:
        return False

    # 延遲導入 Member 實體以避免循環相依
    from app.models.member import Member

    # 查詢有效家長列表
    stmt = select(Member).where(Member.role == "parent", Member.is_active == True)
    result = await db.execute(stmt)
    parents = result.scalars().all()

    # 檢查是否有自訂 PIN 的家長
    has_custom_parent_pins = False
    for parent in parents:
        if parent.pin_code:
            has_custom_parent_pins = True
            if verify_pin(pin, parent.pin_code):
                return True

    # 若無有效家長或皆無自訂 PIN 碼，降級比對 .env 之 PARENT_DEFAULT_PIN
    if not has_custom_parent_pins or len(parents) == 0:
        if pin == settings.PARENT_DEFAULT_PIN.strip():
            return True

    return False

verify_parent_pin = validate_parent_pin

async def verify_member_or_parent_pin(
    db: AsyncSession,
    target_member_id: uuid.UUID,
    input_pin: Optional[str] = None,
    header_pin: Optional[str] = None,
) -> tuple[bool, str]:
    """
    成員或家長 PIN 碼權限驗證:
    1. 取得輸入 PIN (優先 input_pin，其次 header_pin)
    2. 比對有效家長之 PIN 碼 (或 .env PARENT_DEFAULT_PIN)，若相符回傳 (True, "parent")
    3. 比對目標成員 (target_member_id) 之 pin_code，若相符回傳 (True, member.role)
    4. 其餘情況回傳 (False, "none")
    """
    pin = (input_pin or header_pin or "").strip()
    if not pin:
        return False, "none"

    # 1. 優先檢查是否具有家長權限
    if await validate_parent_pin(db, input_pin=pin):
        return True, "parent"

    # 2. 檢查是否符合目標成員的個人 PIN 碼
    from app.models.member import Member
    member = await db.get(Member, target_member_id)
    if not member or not member.is_active:
        return False, "none"

    if member.pin_code:
        if verify_pin(pin, member.pin_code):
            return True, member.role
    else:
        # 未自訂 PIN 碼前，預設允許 0000
        if pin == "0000":
            return True, member.role

    return False, "none"

async def require_parent_pin_dep(
    x_parent_pin: Optional[str] = Header(None, alias="X-Parent-PIN"),
) -> Optional[str]:
    """FastAPI header dependency for X-Parent-PIN"""
    return x_parent_pin

async def require_any_pin_dep(
    x_parent_pin: Optional[str] = Header(None, alias="X-Parent-PIN"),
    x_member_pin: Optional[str] = Header(None, alias="X-Member-PIN"),
) -> Optional[str]:
    """FastAPI header dependency for X-Parent-PIN or X-Member-PIN"""
    return x_parent_pin or x_member_pin

