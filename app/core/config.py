import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = ROOT_DIR / ".env"

# 載入 .env 檔案
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH, override=True)

def _get_database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    pwd = os.getenv("DB_PASSWORD", "").strip()
    user = os.getenv("DB_USER", "postgres").strip()
    host = os.getenv("DB_HOST", "localhost").strip()
    port = os.getenv("DB_PORT", "5432").strip()
    name = os.getenv("DB_NAME", "frog_kudos").strip()

    if not url:
        if pwd:
            return f"postgresql+asyncpg://{user}:{pwd}@{host}:{port}/{name}"
        return f"postgresql+asyncpg://{user}@{host}:{port}/{name}"

    # 若 DATABASE_URL 缺少密碼但 DB_PASSWORD 有值，自動注入密碼保持同步
    if pwd and f":{pwd}@" not in url and "@" in url:
        prefix, rest = url.split("@", 1)
        user_part = prefix.split("//")[-1]
        if ":" not in user_part:
            schema = prefix.split("//")[0] + "//"
            return f"{schema}{user_part}:{pwd}@{rest}"

    return url

class Settings(BaseModel):
    DATABASE_URL: str = Field(default_factory=_get_database_url)
    DB_NAME: str = Field(default_factory=lambda: os.getenv("DB_NAME", "frog_kudos"))
    DB_USER: str = Field(default_factory=lambda: os.getenv("DB_USER", "postgres"))
    DB_PASSWORD: str = Field(default_factory=lambda: os.getenv("DB_PASSWORD", ""))
    DB_HOST: str = Field(default_factory=lambda: os.getenv("DB_HOST", "localhost"))
    DB_PORT: int = Field(default_factory=lambda: int(os.getenv("DB_PORT", "5432")))
    PORT: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    BACKUP_DIR: str = Field(default_factory=lambda: os.getenv("BACKUP_DIR", str(ROOT_DIR / "backups")))
    AUTO_BACKUP: bool = Field(default_factory=lambda: os.getenv("AUTO_BACKUP", "true").lower() in ("true", "1", "yes"))
    BACKUP_RETENTION_COUNT: int = Field(default_factory=lambda: int(os.getenv("BACKUP_RETENTION_COUNT", "10")))
    PARENT_DEFAULT_PIN: str = Field(default_factory=lambda: os.getenv("PARENT_DEFAULT_PIN", "0000"))
    GITHUB_REPO: str = Field(default_factory=lambda: os.getenv("GITHUB_REPO", "chinsonyeh/frog_kudos"))
    LINE_CHANNEL_ACCESS_TOKEN: Optional[str] = Field(default_factory=lambda: os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or None)
    LINE_USER_ID: Optional[str] = Field(default_factory=lambda: os.getenv("LINE_USER_ID") or None)

settings = Settings()

def reload_settings() -> Settings:
    """Reload settings from .env file."""
    global settings
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH, override=True)
    settings = Settings()
    return settings

def get_settings() -> Settings:
    """Get current application settings."""
    return settings

