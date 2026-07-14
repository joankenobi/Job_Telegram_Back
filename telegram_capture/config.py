import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DOWNLOADS_DIR = BASE_DIR / "downloads"

load_dotenv()

API_ID = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")
SESSION_NAME = os.getenv("TG_SESSION", "telegram_capture")

DATABASE_PATH = DATA_DIR / "capture.db"


def get_channel_folder(channel_id: str, channel_title: str | None) -> Path:
    if channel_id.lstrip("-").isdigit():
        folder_name = f"private_{channel_title}" if channel_title else f"private_{channel_id}"
    else:
        folder_name = channel_id.lstrip("@")
    return DOWNLOADS_DIR / folder_name