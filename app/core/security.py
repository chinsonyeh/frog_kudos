import uuid
import time
import bcrypt
from typing import Optional, Dict
from fastapi import HTTPException, Header, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings

# 各瀏覽器獨立 Session 儲存 (Per-Browser Session Store)
# key: session_token (str) -> dict: {"member_id": str, "role": str, "name": str, "avatar": str, "created_at": float, "last_active": float}
PARENT_SESSION_TIMEOUT_SECONDS = 15 * 60  # 15 分鐘
USER_SESSIONS: Dict[str, dict] = {}
PARENT_SESSIONS = USER_SESSIONS  # 相容性別名

def create_user_session(
    member_id: uuid.UUID,
    role: str,
    name: str = "",
    avatar: str = ""
) -> str:
    """簽發專屬此瀏覽器之獨立用戶 Session Token (家長或小孩)"""
    token = f"fks_{uuid.uuid4().hex}"
    now = time.time()
    USER_SESSIONS[token] = {
        "member_id": str(member_id),
        "role": role,
        "name": name,
        "avatar": avatar,
        "created_at": now,
        "last_active": now,
    }
    return token

def create_parent_session(
    member_id: Optional[uuid.UUID] = None,
    name: str = "家長",
    avatar: str = "🔐"
) -> str:
    """相容性：簽發家長獨立 Session Token"""
    return create_user_session(
        member_id=member_id or uuid.uuid4(),
        role="parent",
        name=name,
        avatar=avatar,
    )

def revoke_user_session(token: str) -> bool:
    """銷毀指定之瀏覽器 Session Token"""
    if token and token in USER_SESSIONS:
        del USER_SESSIONS[token]
        return True
    return False

revoke_parent_session = revoke_user_session

def get_user_session(token: Optional[str]) -> Optional[dict]:
    """取得指定瀏覽器 Session Token 並滑動續期 (15 分鐘)"""
    if not token or token not in USER_SESSIONS:
        return None
    session = USER_SESSIONS[token]
    now = time.time()
    if now - session["last_active"] > PARENT_SESSION_TIMEOUT_SECONDS:
        del USER_SESSIONS[token]
        return None
    session["last_active"] = now
    return session

def validate_parent_session(token: Optional[str]) -> bool:
    """驗證指定瀏覽器 Session Token 是否為有效且未超時之家長會話"""
    sess = get_user_session(token)
    return sess is not None and sess.get("role") == "parent"

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
    家長權限驗證機制 (支援各瀏覽器獨立 Session Token 與 PIN 碼):
    1. 優先檢查是否為有效之家長 Session Token
    2. 比對所有 role='parent' 且 is_active=TRUE 的家長成員之 pin_code
    3. 若系統尚無任何有效家長 (冷啟動) 或家長尚未自訂 PIN，自動降級比對 .env 的 PARENT_DEFAULT_PIN
    """
    pin = (input_pin or header_pin or "").strip()
    if not pin:
        return False

    # 1. 優先檢查是否為各瀏覽器之獨立家長 Session Token
    if validate_parent_session(pin):
        return True

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
    成員或家長身分與權限驗證:
    1. 取得輸入 PIN 或 Token
    2. 若為 Session Token:
       - 家長 Session: 允許為所有成員操作，回傳 (True, "parent")
       - 小孩 Session: 僅允許為自身 (target_member_id == session.member_id) 操作，回傳 (True, "child")；絕不允許跨成員操作！
    3. 若為明文 PIN 碼:
       - 符合家長 PIN: 允許 (True, "parent")
       - 符合目標成員個人 PIN: 允許 (True, member.role)
    """
    pin = (input_pin or header_pin or "").strip()
    if not pin:
        return False, "none"

    # 1. 檢查是否為獨立 Session Token
    sess = get_user_session(pin)
    if sess:
        if sess.get("role") == "parent":
            return True, "parent"
        if sess.get("role") == "child":
            if str(sess.get("member_id")) == str(target_member_id):
                return True, "child"
            # 小孩 Session 試圖為他人操作，嚴格拒絕
            return False, "none"

    # 2. 檢查是否符合有效家長之 PIN 碼 (或 .env PARENT_DEFAULT_PIN)
    if await validate_parent_pin(db, input_pin=pin):
        return True, "parent"

    # 3. 檢查是否符合目標成員的個人 PIN 碼
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
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token"),
    x_parent_session: Optional[str] = Header(None, alias="X-Parent-Session"),
    x_parent_pin: Optional[str] = Header(None, alias="X-Parent-PIN"),
) -> Optional[str]:
    """FastAPI header dependency for parent auth"""
    return x_session_token or x_parent_session or x_parent_pin

async def require_any_pin_dep(
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token"),
    x_parent_session: Optional[str] = Header(None, alias="X-Parent-Session"),
    x_parent_pin: Optional[str] = Header(None, alias="X-Parent-PIN"),
    x_member_pin: Optional[str] = Header(None, alias="X-Member-PIN"),
) -> Optional[str]:
    """FastAPI header dependency for any role auth"""
    return x_session_token or x_parent_session or x_parent_pin or x_member_pin

