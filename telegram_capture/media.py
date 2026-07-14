import asyncio
from pathlib import Path
from datetime import datetime

from telethon.types import Message as TelethonMessage, Photo, Document

from .config import get_channel_folder, DOWNLOADS_DIR
from .models import Message, MediaType


IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "svg"}
VIDEO_EXTS = {"mp4", "mkv", "avi", "mov", "webm", "flv", "m4v"}


def guess_extension(file_name: str | None, mime_type: str | None) -> str:
    if file_name and "." in file_name:
        return file_name.rsplit(".", 1)[-1].lower()
    if mime_type:
        if mime_type.startswith("image/"):
            return mime_type.split("/")[-1]
        if mime_type.startswith("video/"):
            return mime_type.split("/")[-1]
    return "bin"


def get_media_type(message: TelethonMessage) -> MediaType:
    if message.photo:
        return MediaType.IMAGE
    if message.video:
        return MediaType.VIDEO
    if message.document:
        mime = message.document.mime_type or ""
        if mime.startswith("image/"):
            return MediaType.IMAGE
        if mime.startswith("video/"):
            return MediaType.VIDEO
    return MediaType.NONE


def get_file_ext(message: TelethonMessage) -> str:
    ext = "bin"
    if message.photo:
        ext = "jpg"
    elif message.video:
        ext = "mp4"
    elif message.document:
        ext = guess_extension(
            message.document.attributes[0].file_name
            if (hasattr(message.document.attributes[0], "file_name"))
            else None,
            message.document.mime_type,
        )
    return ext


async def download_media(
    message: TelethonMessage,
    channel_id: str,
    channel_title: str | None,
) -> tuple[str | None, MediaType]:
    media_type = get_media_type(message)
    if media_type == MediaType.NONE:
        return None, media_type

    date_str = message.date.strftime("%Y%m%d")
    folder = get_channel_folder(channel_id, channel_title)
    # Create date subfolder
    date_folder = folder / date_str
    date_folder.mkdir(parents=True, exist_ok=True)

    file_ext = get_file_ext(message)
    file_name = f"{message.id}_{date_str}.{file_ext}"
    file_path = date_folder / file_name

    if file_path.exists():
        return str(file_path), media_type

    try:
        await message.download_media(file=str(file_path))
    except Exception:
        return None, media_type

    return str(file_path), media_type