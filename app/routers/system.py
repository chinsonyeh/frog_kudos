import os
import shutil
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, File, Form, Header, status
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import (
    verify_parent_pin,
    verify_member_or_parent_pin,
    require_parent_pin_dep,
    create_parent_session,
    create_user_session,
    revoke_parent_session,
    PARENT_SESSION_TIMEOUT_SECONDS,
)
from app.schemas.system import (
    SystemConfigOut,
    SystemConfigUpdate,
    BackupCreate,
    BackupResult,
    BackupFileInfo,
    LineTestIn,
    LineTestOut,
    VersionOut,
    UpgradeRequest,
    UpgradeStatusOut,
    PinVerifyIn,
    PinVerifyOut,
    SessionLockIn,
    MemberPinVerifyIn,
    MemberPinVerifyOut,
    SystemIconIn,
)
from app.services.system_service import (
    run_backup,
    list_backups,
    get_system_config,
    update_system_config,
    check_github_version,
    run_upgrade_process,
    get_upgrade_status,
)
from app.services.line_service import test_line_push

router = APIRouter(prefix="/system", tags=["System Management & Maintenance"])

@router.get("/config", response_model=SystemConfigOut)
async def read_system_config():
    """Web 取得備份、排程、LINE 通知與系統配置 (密碼強制脫敏，NFR-4)"""
    return get_system_config()

@router.put("/config")
async def save_system_config(
    config_in: SystemConfigUpdate,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """Web 儲存自訂備份路徑、排程與 LINE 通知憑證至 .env 檔案（需家長安全鎖）"""
    pin = config_in.parent_pin or x_parent_pin
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    update_system_config(config_in)
    return {"success": True, "message": "系統設定已更新並持久化保存"}

@router.post("/backup", response_model=BackupResult)
async def trigger_backup(
    backup_in: BackupCreate,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """觸發資料庫備份至指定目標路徑 (FR-8)"""
    pin = backup_in.parent_pin or x_parent_pin
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    return await run_backup(target_path=backup_in.target_path)

@router.get("/backups", response_model=List[BackupFileInfo])
async def get_backups(
    target_path: Optional[str] = Query(None, description="指定查詢目錄"),
):
    """查詢指定目錄歷史備份清單 (FR-8)"""
    return await list_backups(target_path=target_path)

@router.post("/line/test", response_model=LineTestOut)
async def trigger_line_test(
    test_in: LineTestIn,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """測試發送 LINE Messaging API 推播訊息 (FR-19)"""
    pin = test_in.parent_pin or x_parent_pin
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    success, msg = await test_line_push()
    return LineTestOut(success=success, message=msg)

@router.get("/version", response_model=VersionOut)
async def get_version_info():
    """連線 GitHub Releases API 檢查最新發行版 (FR-9)"""
    return await check_github_version()

@router.post("/upgrade")
async def trigger_auto_upgrade(
    upgrade_in: UpgradeRequest,
    background_tasks: BackgroundTasks,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """Web 一鍵從 GitHub 下載發行包並自動升級 (FR-9)"""
    pin = upgrade_in.parent_pin or x_parent_pin
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    background_tasks.add_task(run_upgrade_process, upgrade_in.package_url)
    return {"status": "STARTED", "message": "升級程序已於背景啟動，請輪詢 /api/system/upgrade-status 檢視進度"}

@router.post("/upload-package")
async def upload_offline_package(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    parent_pin: Optional[str] = Form(None),
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """手動上傳離線安裝/升級套件 (.tar.gz) 進行升級 (FR-9)"""
    pin = parent_pin or x_parent_pin
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    if not file.filename.endswith(".tar.gz"):
        raise HTTPException(status_code=400, detail="僅支援 .tar.gz 格式之升級套件")

    tmp_path = f"/tmp/{file.filename}"
    with open(tmp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    background_tasks.add_task(run_upgrade_process, tmp_path)
    return {"status": "STARTED", "message": "離線套件上傳成功，升級程序已於背景啟動"}

@router.get("/upgrade-status", response_model=UpgradeStatusOut)
async def check_upgrade_status():
    """Web 輪詢即時升級進度與日誌 (FR-9)"""
    return get_upgrade_status()

@router.post("/verify-pin", response_model=PinVerifyOut)
async def verify_parent_pin_endpoint(
    verify_in: Optional[PinVerifyIn] = None,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """
    即時驗證家長 PIN 碼並簽發專屬此瀏覽器之獨立 Session Token (FR-13)
    驗證成功回傳 200 與獨立 session_token，錯誤拋出 403 Forbidden。
    """
    from app.models.member import Member
    pin = (verify_in.parent_pin if verify_in and verify_in.parent_pin else None) or \
          (verify_in.pin if verify_in and verify_in.pin else None) or \
          x_parent_pin

    # Case A: 指定成員解鎖 (家長或小孩)
    if verify_in and verify_in.member_id:
        member = await db.get(Member, verify_in.member_id)
        if not member or not member.is_active:
            raise HTTPException(status_code=404, detail="成員不存在或已被停用")

        valid, role = await verify_member_or_parent_pin(db, verify_in.member_id, pin)
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"「{member.name}」的 PIN 碼驗證錯誤，請重新輸入",
            )
        session_token = create_user_session(
            member_id=member.id,
            role=member.role,
            name=member.name,
            avatar=member.avatar or "🐸",
        )
        return PinVerifyOut(
            valid=True,
            message=f"{member.name} 解鎖成功",
            role=member.role,
            member_id=member.id,
            member_name=member.name,
            member_avatar=member.avatar or "🐸",
            session_token=session_token,
            expires_in=PARENT_SESSION_TIMEOUT_SECONDS,
        )

    # Case B: 未指定成員之傳統家長解鎖
    if not await verify_parent_pin(db, pin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="家長安全鎖 PIN 碼錯誤，請重新輸入",
        )

    parent_stmt = select(Member).where(Member.role == "parent", Member.is_active == True)
    parent_res = await db.execute(parent_stmt)
    parent_m = parent_res.scalars().first()
    m_id = parent_m.id if parent_m else uuid.uuid4()
    m_name = parent_m.name if parent_m else "家長"
    m_avatar = parent_m.avatar if parent_m else "🔐"

    session_token = create_user_session(
        member_id=m_id,
        role="parent",
        name=m_name,
        avatar=m_avatar,
    )
    return PinVerifyOut(
        valid=True,
        message="家長安全鎖 PIN 碼驗證成功",
        role="parent",
        member_id=m_id,
        member_name=m_name,
        member_avatar=m_avatar,
        session_token=session_token,
        expires_in=PARENT_SESSION_TIMEOUT_SECONDS,
    )

@router.post("/lock-session")
async def lock_session_endpoint(
    lock_in: Optional[SessionLockIn] = None,
    x_parent_session: Optional[str] = Header(None, alias="X-Parent-Session"),
):
    """銷毀指定之瀏覽器 Session Token，即刻在伺服器端鎖定"""
    token = (lock_in.session_token if lock_in and lock_in.session_token else None) or x_parent_session
    if token:
        revoke_parent_session(token)
    return {"success": True, "message": "該瀏覽器會話已安全鎖定"}

@router.post("/verify-member-pin", response_model=MemberPinVerifyOut)
async def verify_member_pin_endpoint(
    verify_in: MemberPinVerifyIn,
    db: AsyncSession = Depends(get_db),
):
    """
    即時驗證特定成員的個人 PIN 碼 (或家長 PIN 碼)
    驗證成功回傳 200 與角色 (parent/child)，錯誤拋出 403 Forbidden。
    """
    valid, role = await verify_member_or_parent_pin(db, verify_in.member_id, verify_in.pin)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="PIN 碼錯誤，請重新輸入",
        )
    return MemberPinVerifyOut(valid=True, role=role, message="PIN 碼驗證成功")

@router.post("/icon")
async def update_system_icon(
    icon_in: SystemIconIn,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
):
    """
    將選定的青蛙圖示設為全站 PWA / 桌面 App 圖示 (需家長權限)
    """
    import subprocess
    import sys
    
    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scripts", "apply_icon.py")
    res = subprocess.run([sys.executable, script_path, icon_in.icon_id], capture_output=True, text=True)
    if res.returncode != 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=res.stderr or "套用圖示失敗",
        )
    return {"success": True, "message": f"成功套用青蛙圖示 #{icon_in.icon_id} 為全站 PWA 圖示", "detail": res.stdout}


