import os
import logging
import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.core.database import engine
from app.routers import (
    members_router,
    categories_router,
    rules_router,
    kudos_router,
    items_router,
    redemptions_router,
    system_router,
    badges_router,
)
from app.services.system_service import run_backup

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("frog_kudos")

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
VERSION_FILE = ROOT_DIR / "VERSION"

# 1. 強制註冊 PWA Manifest 標準 MIME 類型 (FR-12, Section 4.8)
mimetypes.add_type("application/manifest+json", ".webmanifest")

scheduler = AsyncIOScheduler()

async def scheduled_backup_job():
    """定期自動備份任務 (FR-16: 每週日深夜 02:00 自動執行)"""
    logger.info("⏰ 觸發定期自動資料庫備份任務...")
    try:
        res = await run_backup()
        logger.info(f"✅ 定期自動備份成功: {res.backup_file} ({res.file_size})")
    except Exception as e:
        logger.error(f"❌ 定期自動備份失敗: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時生命週期
    settings = get_settings()
    # 2. 安全連線字串脫敏日誌 (NFR-4, Section 8.4)
    safe_db_url = engine.url.render_as_string(hide_password=True)
    logger.info(f"🐸 Frog Kudos 伺服器啟動中... 資料庫連線至: {safe_db_url}")

    # 3. 啟動定期自動備份排程 (FR-16)
    if settings.AUTO_BACKUP:
        # 每週日深夜 02:00
        scheduler.add_job(
            scheduled_backup_job,
            CronTrigger(day_of_week="sun", hour=2, minute=0),
            id="weekly_backup",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("📦 自動備份排程已啟用: 每週日深夜 02:00 自動備份")

    yield

    # 關閉時生命週期
    if scheduler.running:
        scheduler.shutdown()
    logger.info("🐸 Frog Kudos 伺服器已安全停止。")

app = FastAPI(
    title="Frog Kudos API",
    description="家庭積分獎勵系統後端核心服務與 REST APIs",
    version=VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else "1.0.0",
    lifespan=lifespan,
)

# 4. CORS 中介軟體配置 (支援 Vite 開發伺服器 Port 5173，Section 1.2)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. 掛載業務 API 路由 (均掛載於 /api 前綴下)
app.include_router(members_router, prefix="/api")
app.include_router(categories_router, prefix="/api")
app.include_router(rules_router, prefix="/api")
app.include_router(kudos_router, prefix="/api")
app.include_router(items_router, prefix="/api")
app.include_router(redemptions_router, prefix="/api")
app.include_router(system_router, prefix="/api")
app.include_router(badges_router, prefix="/api")

@app.get("/api/health")
async def health_check():
    """系統健康檢查端點"""
    ver = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else "1.0.0"
    return {"status": "ok", "app": "Frog Kudos", "version": ver}

# 6. PWA Manifest 雙路徑別名相容路由 (FR-12, Section 4.8)
@app.get("/manifest.webmanifest", include_in_schema=False)
@app.get("/manifest.json", include_in_schema=False)
@app.get("/site.webmanifest", include_in_schema=False)
async def serve_manifest():
    manifest_path = FRONTEND_DIST / "manifest.webmanifest"
    if not manifest_path.exists():
        manifest_path = FRONTEND_DIST / "manifest.json"
    if manifest_path.exists():
        return FileResponse(str(manifest_path), media_type="application/manifest+json")
    return JSONResponse(
        status_code=404,
        content={"error": "Manifest not found. Frontend dist has not been generated yet."},
    )

# 7. 靜態資源與自訂上傳檔案掛載
UPLOADS_DIR = ROOT_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

# 8. Vue Router SPA 路由 Fallback 防 404 機制 (Section 1.1 #5)
@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(request: Request, full_path: str):
    # 若請求以 api/ 開頭，不作前端攔截 (讓 FastAPI 自動處理 404)
    if full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    target_file = FRONTEND_DIST / full_path
    if full_path and target_file.is_file():
        # 如果是 dist 根目錄下的靜態檔案 (如 favicon.ico, icons/*)
        mime_type, _ = mimetypes.guess_type(str(target_file))
        return FileResponse(str(target_file), media_type=mime_type or "application/octet-stream")

    index_html = FRONTEND_DIST / "index.html"
    if index_html.exists():
        return FileResponse(str(index_html))

    # 若前端尚未編譯，提供友善提示
    return JSONResponse(
        content={
            "app": "Frog Kudos API",
            "message": "FastAPI 後端核心服務運行中。前端靜態資源尚未編譯 (將於 Phase 3 前端開發時建置)。",
            "docs": "/docs",
        }
    )
