import os
import re
import glob
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
import httpx
from fastapi import HTTPException
from app.core.config import get_settings
from app.schemas.system import (
    BackupFileInfo,
    BackupResult,
    SystemConfigOut,
    SystemConfigUpdate,
    VersionOut,
    UpgradeStatusOut,
)

logger = logging.getLogger(__name__)

# 全域即時升級狀態追蹤器 (In-Memory Tracker)
class UpgradeTracker:
    def __init__(self):
        self.status = "IDLE"  # IDLE, RUNNING, COMPLETED, FAILED
        self.progress = 0
        self.current_step = "待命中"
        self.logs: List[str] = []

    def reset(self):
        self.status = "IDLE"
        self.progress = 0
        self.current_step = "待命中"
        self.logs = []

    def update(self, status: str, progress: int, step: str, log_msg: Optional[str] = None):
        self.status = status
        self.progress = progress
        self.current_step = step
        if log_msg:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.logs.append(f"[{timestamp}] {log_msg}")

upgrade_tracker = UpgradeTracker()

async def run_backup(target_path: Optional[str] = None) -> BackupResult:
    """執行資料庫指定路徑備份腳本 (FR-8)"""
    settings = get_settings()
    root_dir = Path(__file__).resolve().parent.parent.parent
    script_path = root_dir / "scripts" / "backup.sh"

    dest_dir = target_path or settings.BACKUP_DIR or str(root_dir / "backups")
    os.makedirs(dest_dir, exist_ok=True)

    cmd = ["bash", str(script_path), dest_dir]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(root_dir),
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        err_msg = stderr.decode().strip() or stdout.decode().strip()
        logger.error(f"備份腳本執行失敗: {err_msg}")
        raise HTTPException(status_code=500, detail=f"備份腳本執行失敗: {err_msg}")

    # 尋找該目錄下最新產生的 .dump 檔案
    dump_files = glob.glob(os.path.join(dest_dir, "frog_kudos_backup_*.dump"))
    if not dump_files:
        raise HTTPException(status_code=500, detail="備份完成但未找到產生的 dump 檔案")

    latest_file = max(dump_files, key=os.path.getmtime)
    file_stat = os.stat(latest_file)
    size_kb = round(file_stat.st_size / 1024, 2)
    created_at = datetime.fromtimestamp(file_stat.st_mtime, tz=timezone.utc)

    return BackupResult(
        success=True,
        backup_file=os.path.basename(latest_file),
        file_size=f"{size_kb} KB",
        created_at=created_at,
    )

async def list_backups(target_path: Optional[str] = None) -> List[BackupFileInfo]:
    """取得指定目錄之歷史備份清單"""
    settings = get_settings()
    root_dir = Path(__file__).resolve().parent.parent.parent
    dest_dir = target_path or settings.BACKUP_DIR or str(root_dir / "backups")

    if not os.path.exists(dest_dir):
        return []

    dump_files = glob.glob(os.path.join(dest_dir, "frog_kudos_backup_*.dump"))
    dump_files.sort(key=os.path.getmtime, reverse=True)

    results: List[BackupFileInfo] = []
    for f in dump_files:
        st = os.stat(f)
        size_kb = round(st.st_size / 1024, 2)
        results.append(
            BackupFileInfo(
                filename=os.path.basename(f),
                path=f,
                size=f"{size_kb} KB",
                created_at=datetime.fromtimestamp(st.st_mtime, tz=timezone.utc),
            )
        )
    return results

def get_system_config() -> SystemConfigOut:
    """取得系統安全脫敏設定 (FR-8, FR-16, FR-19, NFR-4)"""
    settings = get_settings()
    root_dir = Path(__file__).resolve().parent.parent.parent
    b_dir = settings.BACKUP_DIR or str(root_dir / "backups")

    return SystemConfigOut(
        backup_dir=b_dir,
        port=settings.PORT,
        db_name=settings.DB_NAME,
        github_repo=settings.GITHUB_REPO,
        auto_backup=settings.AUTO_BACKUP,
        retention_count=settings.BACKUP_RETENTION_COUNT,
        line_configured=bool(settings.LINE_CHANNEL_ACCESS_TOKEN and settings.LINE_USER_ID),
        line_user_id=settings.LINE_USER_ID,
    )

def update_system_config(update_in: SystemConfigUpdate) -> bool:
    """持久化更新設定至專案 .env 檔案並鎖定 chmod 600"""
    root_dir = Path(__file__).resolve().parent.parent.parent
    env_path = root_dir / ".env"

    env_lines: List[str] = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            env_lines = f.readlines()

    updates: Dict[str, str] = {}
    if update_in.backup_dir is not None:
        updates["BACKUP_DIR"] = update_in.backup_dir.strip()
    if update_in.auto_backup is not None:
        updates["AUTO_BACKUP"] = "true" if update_in.auto_backup else "false"
    if update_in.retention_count is not None:
        updates["BACKUP_RETENTION_COUNT"] = str(update_in.retention_count)
    if update_in.line_channel_access_token is not None:
        updates["LINE_CHANNEL_ACCESS_TOKEN"] = update_in.line_channel_access_token.strip()
    if update_in.line_user_id is not None:
        updates["LINE_USER_ID"] = update_in.line_user_id.strip()

    new_lines = []
    seen_keys = set()
    for line in env_lines:
        match = re.match(r"^([A-Z0-9_]+)=(.*)$", line.strip())
        if match:
            key = match.group(1)
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                seen_keys.add(key)
                continue
        new_lines.append(line)

    for k, v in updates.items():
        if k not in seen_keys:
            new_lines.append(f"{k}={v}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    # 確保 chmod 600 安全權限 (NFR-4)
    try:
        os.chmod(env_path, 0o600)
    except Exception as e:
        logger.warning(f"無法設定 .env 權限為 600: {e}")

    return True

async def check_github_version() -> VersionOut:
    """連線 GitHub Releases API 檢查最新發行版 (FR-9)"""
    settings = get_settings()
    root_dir = Path(__file__).resolve().parent.parent.parent
    version_file = root_dir / "VERSION"

    current_ver = "v1.0.0"
    if version_file.exists():
        current_ver = version_file.read_text(encoding="utf-8").strip()

    repo = settings.GITHUB_REPO or "chinsonyeh/frog_kudos"
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(api_url, headers={"User-Agent": "Frog-Kudos-Updater"})
            if resp.status_code == 200:
                data = resp.json()
                latest_tag = data.get("tag_name")
                body = data.get("body", "")
                download_url = None
                for asset in data.get("assets", []):
                    if asset.get("name", "").endswith(".tar.gz"):
                        download_url = asset.get("browser_download_url")
                        break

                has_update = bool(latest_tag and latest_tag != current_ver)
                return VersionOut(
                    current_version=current_ver,
                    latest_version=latest_tag,
                    has_update=has_update,
                    release_notes=body,
                    download_url=download_url,
                )
    except Exception as e:
        logger.warning(f"檢查 GitHub 版本時發生錯誤: {e}")

    return VersionOut(
        current_version=current_ver,
        latest_version=None,
        has_update=False,
        release_notes=None,
        download_url=None,
    )

async def run_upgrade_process(package_path_or_url: Optional[str] = None):
    """非同步執行系統升級背景任務 (FR-9, 6.6)"""
    root_dir = Path(__file__).resolve().parent.parent.parent
    upgrade_script = root_dir / "scripts" / "upgrade.sh"

    upgrade_tracker.reset()
    upgrade_tracker.update("RUNNING", 10, "準備執行升級前置檢查...", "啟動平滑升級程序")

    cmd = ["bash", str(upgrade_script)]
    if package_path_or_url:
        cmd.append(package_path_or_url)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(root_dir),
        )

        upgrade_tracker.update("RUNNING", 25, "正在執行資料庫強制備份與下載發行包...", "調用 scripts/upgrade.sh")

        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            text = line.decode().strip()
            if text:
                upgrade_tracker.logs.append(text)
                if "步驟 1" in text:
                    upgrade_tracker.update("RUNNING", 30, "執行升級前強制資料庫備份")
                elif "步驟 2" in text:
                    upgrade_tracker.update("RUNNING", 50, "取得升級安裝包")
                elif "步驟 3" in text:
                    upgrade_tracker.update("RUNNING", 70, "解壓縮並套用程式更新")
                elif "步驟 4" in text:
                    upgrade_tracker.update("RUNNING", 80, "更新 Python 相依套件")
                elif "步驟 5" in text:
                    upgrade_tracker.update("RUNNING", 90, "執行資料庫結構遷移 (Migration)")
                elif "步驟 6" in text or "成功升級" in text:
                    upgrade_tracker.update("RUNNING", 95, "清理暫存檔案")

        rc = await proc.wait()
        if rc == 0:
            upgrade_tracker.update("COMPLETED", 100, "升級完成！系統已就緒", "所有升級步驟順利完成！")
        else:
            upgrade_tracker.update("FAILED", upgrade_tracker.progress, "升級過程發生錯誤", f"程序退出代碼: {rc}")
    except Exception as e:
        upgrade_tracker.update("FAILED", upgrade_tracker.progress, f"執行例外: {str(e)}", str(e))

def get_upgrade_status() -> UpgradeStatusOut:
    """取得當前升級狀態與日誌"""
    return UpgradeStatusOut(
        status=upgrade_tracker.status,
        progress=upgrade_tracker.progress,
        current_step=upgrade_tracker.current_step,
        logs=upgrade_tracker.logs,
    )
