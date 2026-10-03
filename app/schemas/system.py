import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class BackupFileInfo(BaseModel):
    filename: str
    path: str
    size: str
    created_at: datetime

class BackupCreate(BaseModel):
    target_path: Optional[str] = None
    parent_pin: Optional[str] = None

class BackupResult(BaseModel):
    success: bool
    backup_file: str
    file_size: str
    created_at: datetime

class SystemConfigOut(BaseModel):
    backup_dir: str
    port: int
    db_name: str
    github_repo: str
    auto_backup: bool
    retention_count: int
    line_configured: bool
    line_user_id: Optional[str] = None

class SystemConfigUpdate(BaseModel):
    backup_dir: Optional[str] = None
    auto_backup: Optional[bool] = None
    retention_count: Optional[int] = Field(default=None, ge=1, le=100)
    line_channel_access_token: Optional[str] = None
    line_user_id: Optional[str] = None
    parent_pin: Optional[str] = None

class LineTestIn(BaseModel):
    parent_pin: Optional[str] = None

class LineTestOut(BaseModel):
    success: bool
    message: str

class VersionOut(BaseModel):
    current_version: str
    latest_version: Optional[str] = None
    has_update: bool = False
    release_notes: Optional[str] = None
    download_url: Optional[str] = None

class UpgradeRequest(BaseModel):
    package_url: Optional[str] = None
    parent_pin: Optional[str] = None

class UpgradeStatusOut(BaseModel):
    status: str  # IDLE, RUNNING, COMPLETED, FAILED
    progress: int
    current_step: str
    logs: List[str]

class PinVerifyIn(BaseModel):
    pin: Optional[str] = None
    parent_pin: Optional[str] = None

class PinVerifyOut(BaseModel):
    valid: bool
    message: str
    session_token: Optional[str] = None
    expires_in: Optional[int] = None

class SessionLockIn(BaseModel):
    session_token: Optional[str] = None

class MemberPinVerifyIn(BaseModel):
    member_id: uuid.UUID
    pin: str

class MemberPinVerifyOut(BaseModel):
    valid: bool
    role: str
    message: str
