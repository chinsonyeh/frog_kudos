import logging
from typing import Tuple
import httpx
from app.core.config import get_settings

logger = logging.getLogger(__name__)

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"

async def send_line_push(message: str) -> bool:
    """
    發送 LINE Messaging API Push 訊息至指定家長 User ID。
    非同步且具備完整例外隔離，任何錯誤僅記錄 Log，絕不拋出異常中斷核心交易 (FR-19, NFR-2)。
    """
    settings = get_settings()
    token = settings.LINE_CHANNEL_ACCESS_TOKEN
    user_id = settings.LINE_USER_ID

    if not token or not user_id:
        logger.info("LINE 推播未啟用或缺少憑證 (LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID)，略過推播。")
        return False

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    payload = {
        "to": user_id,
        "messages": [
            {
                "type": "text",
                "text": message,
            }
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(LINE_PUSH_URL, headers=headers, json=payload)
            if response.status_code == 200:
                logger.info("LINE 推播訊息發送成功。")
                return True
            else:
                logger.warning(
                    f"LINE 推播發送失敗，狀態碼: {response.status_code}, 回應: {response.text}"
                )
                return False
    except Exception as e:
        logger.warning(f"LINE 推播連線或執行例外: {str(e)}")
        return False

async def test_line_push() -> Tuple[bool, str]:
    """
    測試發送 LINE Messaging API 推播訊息，回傳詳細狀態與訊息。
    """
    settings = get_settings()
    token = settings.LINE_CHANNEL_ACCESS_TOKEN
    user_id = settings.LINE_USER_ID

    if not token:
        return False, "尚未設定 LINE Channel Access Token"
    if not user_id:
        return False, "尚未設定家長 LINE User ID"

    test_message = "🐸 [Frog Kudos 系統測試]\nLINE Messaging API 連線推播成功！家庭兌換即時通知功能已就緒。"
    success = await send_line_push(test_message)
    if success:
        return True, "測試推播發送成功！請檢查手機 LINE 聊天室。"
    else:
        return False, "LINE 訊息發送失敗，請檢查 Channel Access Token 與 User ID 是否有效。"
