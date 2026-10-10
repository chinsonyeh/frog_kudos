import uuid
import os
import time
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List
from PIL import Image, ImageOps
from fastapi import APIRouter, Depends, HTTPException, Query, Header, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.core.database import get_db
from app.core.security import verify_parent_pin, hash_pin, require_parent_pin_dep, verify_member_or_parent_pin
from app.models.member import Member
from app.models.kudos_record import KudosRecord
from app.models.redemption import Redemption
from app.schemas.member import MemberCreate, MemberUpdate, MemberAvatarUpdate, MemberOut, MemberChangePinIn
from app.schemas.badge import MemberBadgeOut
from app.services.badge_service import get_member_badges

router = APIRouter(prefix="/members", tags=["Members"])

MAX_CUSTOM_AVATARS = 100

def _validate_image_file(file: UploadFile, contents: bytes):
    valid_content_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    content_type = file.content_type or ""
    filename = (file.filename or "").lower()
    if content_type not in valid_content_types and not any(filename.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
        raise HTTPException(status_code=400, detail="僅支援 JPG、PNG、WebP、GIF 等圖片格式")
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="圖片檔案過大，請選擇 5MB 以內的照片")

def _process_avatar_image(contents: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(contents))
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"無法解析圖片檔案：{e}")

    width, height = image.size
    min_dim = min(width, height)
    left = (width - min_dim) // 2
    top = (height - min_dim) // 2
    right = left + min_dim
    bottom = top + min_dim
    cropped = image.crop((left, top, right, bottom))
    return cropped.resize((256, 256), Image.Resampling.LANCZOS)

@router.get("/avatars/gallery")
async def list_custom_avatars(
    member_id: Optional[uuid.UUID] = Query(None, description="特定成員 ID；若指定則僅列出該成員個人頭像庫"),
):
    """列出已儲存的自訂頭像列表 (若指定 member_id 則列出該成員專屬庫，否則列出全部)"""
    root_dir = Path(__file__).resolve().parent.parent.parent
    avatars_dir = root_dir / "uploads" / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)

    items = []
    if member_id:
        member_dir = avatars_dir / str(member_id)
        if member_dir.exists():
            for f in member_dir.glob("*.webp"):
                if f.is_file():
                    stat = f.stat()
                    items.append({
                        "url": f"/uploads/avatars/{member_id}/{f.name}",
                        "filename": f.name,
                        "size_kb": round(stat.st_size / 1024, 1),
                        "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                        "mtime": stat.st_mtime,
                    })
        # 兼容搜尋 legacy 檔案 ({member_id}_*.webp)
        for f in avatars_dir.glob(f"{member_id}_*.webp"):
            if f.is_file():
                stat = f.stat()
                items.append({
                    "url": f"/uploads/avatars/{f.name}",
                    "filename": f.name,
                    "size_kb": round(stat.st_size / 1024, 1),
                    "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    "mtime": stat.st_mtime,
                })
    else:
        # 全域掃描所有頭像檔案 (含各成員目錄與根目錄)
        for f in avatars_dir.glob("*.webp"):
            if f.is_file():
                stat = f.stat()
                items.append({
                    "url": f"/uploads/avatars/{f.name}",
                    "filename": f.name,
                    "size_kb": round(stat.st_size / 1024, 1),
                    "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    "mtime": stat.st_mtime,
                })
        for sub in avatars_dir.iterdir():
            if sub.is_dir():
                for f in sub.glob("*.webp"):
                    if f.is_file():
                        stat = f.stat()
                        items.append({
                            "url": f"/uploads/avatars/{sub.name}/{f.name}",
                            "filename": f.name,
                            "size_kb": round(stat.st_size / 1024, 1),
                            "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                            "mtime": stat.st_mtime,
                        })

    items.sort(key=lambda x: x["mtime"], reverse=True)
    for it in items:
        del it["mtime"]

    return {
        "member_id": str(member_id) if member_id else None,
        "total": len(items),
        "max_allowed": MAX_CUSTOM_AVATARS,
        "avatars": items,
    }

@router.delete("/avatars/gallery/{filename}")
async def delete_custom_avatar(
    filename: str,
    member_id: Optional[uuid.UUID] = Query(None, description="指定成員 ID"),
    db: AsyncSession = Depends(get_db),
):
    """刪除指定之自訂頭像，若有成員正在使用該圖檔，則將其頭像自動重設為預設青蛙"""
    if not filename.endswith(".webp") or "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="無效的頭像檔案名稱")

    root_dir = Path(__file__).resolve().parent.parent.parent
    avatars_dir = root_dir / "uploads" / "avatars"

    target_file = None
    if member_id:
        cand = avatars_dir / str(member_id) / filename
        if cand.exists() and cand.is_file():
            target_file = cand
    if not target_file:
        cand = avatars_dir / filename
        if cand.exists() and cand.is_file():
            target_file = cand

    # 若尚未找到，搜尋各成員子目錄
    if not target_file:
        for sub in avatars_dir.iterdir():
            if sub.is_dir():
                cand = sub / filename
                if cand.exists() and cand.is_file():
                    target_file = cand
                    break

    if not target_file or not target_file.is_file():
        raise HTTPException(status_code=404, detail="找不到欲刪除的頭像檔案")

    try:
        target_file.unlink()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"無法刪除檔案：{e}")

    # 同步更新正在使用此頭像的成員，改為預設 🐸
    res = await db.execute(select(Member))
    all_members = res.scalars().all()
    affected_count = 0
    for m in all_members:
        if m.avatar and filename in m.avatar:
            m.avatar = "🐸"
            affected_count += 1
    if affected_count > 0:
        await db.commit()

    return {
        "success": True,
        "message": f"已成功刪除頭像 {filename}",
        "affected_members": affected_count,
    }

@router.post("/avatars/gallery/upload")
async def upload_gallery_avatar(
    file: UploadFile = File(...),
    member_id: Optional[uuid.UUID] = Query(None, description="指定成員 ID"),
):
    """上傳自訂頭像相片 (若指定 member_id 則保存至該成員專屬庫，上限 100 個)"""
    contents = await file.read()
    _validate_image_file(file, contents)
    resized = _process_avatar_image(contents)

    root_dir = Path(__file__).resolve().parent.parent.parent
    if member_id:
        target_dir = root_dir / "uploads" / "avatars" / str(member_id)
        url_prefix = f"/uploads/avatars/{member_id}"
    else:
        target_dir = root_dir / "uploads" / "avatars"
        url_prefix = "/uploads/avatars"

    target_dir.mkdir(parents=True, exist_ok=True)
    existing_files = [f for f in target_dir.glob("*.webp") if f.is_file()]
    if len(existing_files) >= MAX_CUSTOM_AVATARS:
        raise HTTPException(status_code=400, detail="自訂頭像庫已達上限 (最多 100 個)，請先刪除不再使用的舊頭像！")

    timestamp = int(time.time() * 1000)
    new_filename = f"{timestamp}_{uuid.uuid4().hex[:6]}.webp"
    save_path = target_dir / new_filename
    resized.save(save_path, "WEBP", quality=88, optimize=True)

    stat = save_path.stat()
    return {
        "member_id": str(member_id) if member_id else None,
        "url": f"{url_prefix}/{new_filename}",
        "filename": new_filename,
        "size_kb": round(stat.st_size / 1024, 1),
        "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }

@router.get("", response_model=List[MemberOut])
async def list_members(
    include_inactive: bool = Query(False, description="是否包含已停用成員"),
    db: AsyncSession = Depends(get_db),
):
    """取得家庭成員清單（預設僅列出有效成員）"""
    stmt = select(Member)
    if not include_inactive:
        stmt = stmt.where(Member.is_active == True)
    stmt = stmt.order_by(Member.created_at.asc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("", response_model=MemberOut)
async def create_member(
    member_in: MemberCreate,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """新增家庭成員（需家長安全鎖）"""
    pin = member_in.parent_pin or x_parent_pin
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    # 檢查姓名是否已存在
    existing = await db.execute(select(Member).where(Member.name == member_in.name.strip()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="成員姓名已存在")

    # 預設 PIN 碼設定在新增用戶的資料庫中 (若未指定則預設 0000 並以 bcrypt 雜湊寫入資料庫)
    # 當用戶日後修改 PIN 碼後，資料庫中的舊值即被替換，系統程式碼中不再保留任何預設 PIN 碼
    pin_val = member_in.pin_code.strip() if member_in.pin_code and member_in.pin_code.strip() else "0000"
    hashed_pin = hash_pin(pin_val)

    new_member = Member(
        id=member_in.id or uuid.uuid4(),
        name=member_in.name.strip(),
        role=member_in.role,
        avatar=member_in.avatar,
        pin_code=hashed_pin,
        current_points=0,
        total_earned_points=0,
        is_active=True,
    )
    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)
    return new_member

@router.put("/{member_id}", response_model=MemberOut)
async def update_member(
    member_id: uuid.UUID,
    member_in: MemberUpdate,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """
    修改家庭成員資訊、變更家長 PIN 碼或停用狀態。
    若僅變更頭像 (avatar)，未解鎖狀態下亦允許變更（無須家長安全鎖）；
    若涉及姓名、角色、PIN 碼、啟用狀態等管理屬性，必須通過家長安全鎖驗證。
    """
    # 檢查是否僅變更頭像 (未解鎖時仍可更換頭像)
    is_avatar_only = (
        member_in.avatar is not None
        and member_in.name is None
        and member_in.role is None
        and member_in.pin_code is None
        and member_in.is_active is None
    )

    if not is_avatar_only:
        pin = member_in.parent_pin or x_parent_pin
        if not await verify_parent_pin(db, pin):
            raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    member = await db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="成員不存在")

    if member_in.name is not None and member_in.name.strip() != member.name:
        existing = await db.execute(select(Member).where(Member.name == member_in.name.strip()))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="成員姓名已被使用")
        member.name = member_in.name.strip()

    if member_in.role is not None:
        member.role = member_in.role
    if member_in.avatar is not None:
        member.avatar = member_in.avatar
    if member_in.pin_code is not None:
        if member_in.pin_code.strip():
            member.pin_code = hash_pin(member_in.pin_code.strip())
    if member_in.is_active is not None:
        member.is_active = member_in.is_active

    await db.commit()
    await db.refresh(member)
    return member

@router.patch("/{member_id}/avatar", response_model=MemberOut)
async def update_member_avatar(
    member_id: uuid.UUID,
    avatar_in: MemberAvatarUpdate,
    db: AsyncSession = Depends(get_db),
):
    """允許小孩或未解鎖模式下自由更換個人代表頭像 (無須家長安全鎖)"""
    member = await db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="成員不存在")
    member.avatar = avatar_in.avatar
    await db.commit()
    await db.refresh(member)
    return member

@router.post("/{member_id}/avatar-upload", response_model=MemberOut)
async def upload_member_avatar(
    member_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    上傳自訂頭像照片 (支援相簿圖片、大頭貼)
    - 檢查檔案大小與圖片格式 (jpg, png, webp, heic 等)
    - 使用 Pillow 自動正方形裁切並縮小至 256x256 WebP
    - 自動清除該成員過去上傳的舊圖檔
    - 更新 member.avatar 為 /uploads/avatars/{member_id}_{timestamp}.webp
    """
    member = await db.get(Member, member_id)
    if not member or not member.is_active:
        raise HTTPException(status_code=404, detail="成員不存在或已停用")

    # 1. 檢查檔案格式
    valid_content_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    content_type = file.content_type or ""
    filename = (file.filename or "").lower()
    if content_type not in valid_content_types and not any(filename.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
        raise HTTPException(status_code=400, detail="僅支援 JPG、PNG、WebP、GIF 等圖片格式")

    # 2. 讀取並檢查檔案大小 (上限 5MB)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="圖片檔案過大，請選擇 5MB 以內的照片")

    # 3. 使用 Pillow 讀取並處理旋轉與正方形中心裁切
    try:
        image = Image.open(io.BytesIO(contents))
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"無法解析圖片檔案：{e}")

    width, height = image.size
    min_dim = min(width, height)
    left = (width - min_dim) // 2
    top = (height - min_dim) // 2
    right = left + min_dim
    bottom = top + min_dim
    cropped = image.crop((left, top, right, bottom))
    resized = cropped.resize((256, 256), Image.Resampling.LANCZOS)

    # 4. 準備儲存目錄並檢查上限 (每人最多 100 個)
    root_dir = Path(__file__).resolve().parent.parent.parent
    member_dir = root_dir / "uploads" / "avatars" / str(member_id)
    member_dir.mkdir(parents=True, exist_ok=True)

    existing_files = [f for f in member_dir.glob("*.webp") if f.is_file()]
    if len(existing_files) >= MAX_CUSTOM_AVATARS:
        raise HTTPException(status_code=400, detail="此成員專屬自訂頭像庫已達上限 (最多 100 個)，請先刪除不再使用的舊頭像！")

    # 5. 輸出新檔案 (儲存裁切縮放後之 256x256 WebP)
    timestamp = int(time.time() * 1000)
    new_filename = f"{timestamp}_{uuid.uuid4().hex[:6]}.webp"
    save_path = member_dir / new_filename
    resized.save(save_path, "WEBP", quality=88, optimize=True)

    # 6. 更新資料庫
    member.avatar = f"/uploads/avatars/{member_id}/{new_filename}"
    await db.commit()
    await db.refresh(member)
    return member

@router.get("/{member_id}/avatars/gallery")
async def list_member_custom_avatars(
    member_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """查詢特定成員個人專屬的自訂頭像庫列表 (每人上限 100 個)，按時間由新到舊排序"""
    root_dir = Path(__file__).resolve().parent.parent.parent
    member_dir = root_dir / "uploads" / "avatars" / str(member_id)
    member_dir.mkdir(parents=True, exist_ok=True)

    files = [f for f in member_dir.glob("*.webp") if f.is_file()]

    # 同時相容檢查根目錄下屬於該成員的 legacy 檔案 ({member_id}_*.webp)
    root_avatars_dir = root_dir / "uploads" / "avatars"
    legacy_files = [f for f in root_avatars_dir.glob(f"{member_id}_*.webp") if f.is_file()]

    items = []
    for f in files:
        stat = f.stat()
        items.append({
            "url": f"/uploads/avatars/{member_id}/{f.name}",
            "filename": f.name,
            "size_kb": round(stat.st_size / 1024, 1),
            "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "mtime": stat.st_mtime,
        })
    for f in legacy_files:
        stat = f.stat()
        items.append({
            "url": f"/uploads/avatars/{f.name}",
            "filename": f.name,
            "size_kb": round(stat.st_size / 1024, 1),
            "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "mtime": stat.st_mtime,
        })

    items.sort(key=lambda x: x["mtime"], reverse=True)
    for it in items:
        del it["mtime"]

    return {
        "member_id": str(member_id),
        "total": len(items),
        "max_allowed": MAX_CUSTOM_AVATARS,
        "avatars": items,
    }

@router.post("/{member_id}/avatars/gallery/upload")
async def upload_member_gallery_avatar(
    member_id: uuid.UUID,
    file: UploadFile = File(...),
):
    """
    上傳相片至該成員專屬的頭像庫 (不立即套用至成員頭像):
    - 檢查檔案大小與圖片格式
    - 使用 Pillow 正方形置中裁切並壓縮為 256x256 WebP
    - 檢查該成員頭像庫上限 (每人最多 100 個)
    - 保存至 uploads/avatars/{member_id}/，回傳相片 URL
    """
    contents = await file.read()
    _validate_image_file(file, contents)
    resized = _process_avatar_image(contents)

    root_dir = Path(__file__).resolve().parent.parent.parent
    member_dir = root_dir / "uploads" / "avatars" / str(member_id)
    member_dir.mkdir(parents=True, exist_ok=True)

    existing_files = [f for f in member_dir.glob("*.webp") if f.is_file()]
    if len(existing_files) >= MAX_CUSTOM_AVATARS:
        raise HTTPException(status_code=400, detail="此成員專屬自訂頭像庫已達上限 (最多 100 個)，請先刪除不再使用的舊頭像！")

    timestamp = int(time.time() * 1000)
    new_filename = f"{timestamp}_{uuid.uuid4().hex[:6]}.webp"
    save_path = member_dir / new_filename
    resized.save(save_path, "WEBP", quality=88, optimize=True)

    stat = save_path.stat()
    return {
        "member_id": str(member_id),
        "url": f"/uploads/avatars/{member_id}/{new_filename}",
        "filename": new_filename,
        "size_kb": round(stat.st_size / 1024, 1),
        "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }

@router.delete("/{member_id}/avatars/gallery/{filename}")
async def delete_member_gallery_avatar(
    member_id: uuid.UUID,
    filename: str,
    db: AsyncSession = Depends(get_db),
):
    """刪除該成員指定之自訂頭像，若該成員目前正使用該圖檔，則自動將其代表頭像重設為預設青蛙"""
    if not filename.endswith(".webp") or "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="無效的頭像檔案名稱")

    root_dir = Path(__file__).resolve().parent.parent.parent
    member_dir = root_dir / "uploads" / "avatars" / str(member_id)
    target_file = member_dir / filename

    legacy_file = root_dir / "uploads" / "avatars" / filename
    if not target_file.exists() and legacy_file.exists() and filename.startswith(f"{member_id}_"):
        target_file = legacy_file

    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(status_code=404, detail="找不到欲刪除的頭像檔案")

    try:
        target_file.unlink()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"無法刪除檔案：{e}")

    # 若該成員正在使用此圖檔，自動復原為 🐸
    member = await db.get(Member, member_id)
    avatar_url_1 = f"/uploads/avatars/{member_id}/{filename}"
    avatar_url_2 = f"/uploads/avatars/{filename}"
    if member and (member.avatar == avatar_url_1 or member.avatar == avatar_url_2):
        member.avatar = "🐸"
        await db.commit()

    return {
        "success": True,
        "message": f"已成功刪除頭像 {filename}",
        "member_id": str(member_id),
    }

@router.post("/{member_id}/change-pin")
async def change_member_pin(
    member_id: uuid.UUID,
    pin_in: MemberChangePinIn,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """
    變更成員個人 PIN 碼:
    - 小孩可輸入目前 PIN 碼驗證後變更為新 PIN 碼
    - 家長亦可輸入家長 PIN 碼直接重設小孩或自己的 PIN 碼
    """
    member = await db.get(Member, member_id)
    if not member or not member.is_active:
        raise HTTPException(status_code=404, detail="成員不存在或已被停用")

    pin_to_verify = pin_in.old_pin or pin_in.parent_pin or x_parent_pin
    valid, _ = await verify_member_or_parent_pin(db, member_id, pin_to_verify)
    if not valid:
        raise HTTPException(status_code=403, detail="目前 PIN 碼驗證錯誤，無法變更")

    if not pin_in.new_pin or len(pin_in.new_pin.strip()) < 4:
        raise HTTPException(status_code=400, detail="新 PIN 碼必須為至少 4 位數字")

    member.pin_code = hash_pin(pin_in.new_pin.strip())
    await db.commit()
    return {"success": True, "message": f"已成功變更「{member.name}」的 PIN 碼"}

@router.delete("/{member_id}")
async def delete_or_deactivate_member(
    member_id: uuid.UUID,
    parent_pin: Optional[str] = None,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """
    安全刪除或停用成員 (FR-1)
    若已有歷史紀錄則轉為軟停用 (is_active=False) 以保全審計鏈；若為全新無紀錄成員則實體刪除。
    """
    pin = parent_pin or x_parent_pin
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    member = await db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="成員不存在")

    # 檢查是否有歷史紀錄
    kudos_count_res = await db.execute(
        select(func.count(KudosRecord.id)).where(KudosRecord.member_id == member_id)
    )
    kudos_count = kudos_count_res.scalar() or 0

    red_count_res = await db.execute(
        select(func.count(Redemption.id)).where(Redemption.member_id == member_id)
    )
    red_count = red_count_res.scalar() or 0

    if kudos_count > 0 or red_count > 0:
        member.is_active = False
        await db.commit()
        return {"success": True, "action": "DEACTIVATED", "message": "成員已有歷史紀錄，已自動轉為停用狀態"}
    else:
        await db.delete(member)
        await db.commit()
        return {"success": True, "action": "DELETED", "message": "全新成員無歷史紀錄，已徹底刪除"}

@router.get("/{member_id}/badges", response_model=List[MemberBadgeOut])
async def list_member_badges(
    member_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """查詢成員里程碑成就勳章清單與達成進度 (FR-18)"""
    return await get_member_badges(db, member_id)
