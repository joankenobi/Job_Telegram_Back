import asyncio
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

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

async def get_folder_for_message(message:Message) -> str:
    """
        Return the file path and file name without the file extension.
 
    """
    try:
        date_str= message.date.strftime("%Y%m%d")
        folder = get_channel_folder(message.channel_id, message.channel_title)
        date_folder = folder / date_str
        date_folder.mkdir(parents=True, exist_ok=True)
        file_name = f"{message.message_id}_{date_str}"
        file_path = date_folder / file_name
    
        if date_folder.exists():
            return str(file_path)

    except Exception as e:
        print(e)



def get_primary_location(location: str | None) -> str:
    """Extract primary location from comma-separated locations string.
    Returns the first location, or 'no_location' if None/empty."""
    if not location or not location.strip():
        return "no_location"
    locations = location.split(",")
    primary = locations[0].strip()
    return primary if primary else "no_location"


def get_location_folder(base_folder: Path, location: str) -> Path:
    """Get the folder path for a specific location within the base folder."""
    # Sanitize location name for filesystem
    safe_location = "".join(c for c in location if c.isalnum() or c in (" ", "-", "_")).strip()
    safe_location = safe_location.replace(" ", "_")
    # return base_folder / Path("locations") / safe_location
    return base_folder / Path("locations")


async def copy_media_to_location_folder(
    message: Message,
    base_folder: Path,
) -> tuple[bool, str | None]:
    """Copy a media file to its location-based folder.
    Returns (success, destination_path or error_message)."""
    if not message.media_path:
        return False, "No media path"
    
    src_path = Path(message.media_path)
    if not src_path.exists():
        return False, f"Source file not found: {src_path}"
    
    primary_location = get_primary_location(message.location)
    location_folder = get_location_folder(base_folder, primary_location)
    location_folder.mkdir(parents=True, exist_ok=True)
    
    dest_path = location_folder / src_path.name
    
    # Avoid overwriting - add suffix if file exists
    counter = 1
    original_dest = dest_path
    while dest_path.exists():
        stem = original_dest.stem
        suffix = original_dest.suffix
        dest_path = location_folder / f"{stem}_{counter}{suffix}"
        counter += 1
    
    try:
        shutil.copy2(src_path, dest_path)
        return True, str(dest_path)
    except Exception as e:
        return False, f"Copy failed: {e}"


async def classify_media_by_location(
    messages: list[Message],
    base_folder: Path,
) -> dict[str, list[tuple[Message, bool, str | None]]]:
    """Classify and copy media files into location-based folders.
    Returns dict with location as key and list of (message, success, dest_path/error) as value."""
    results: dict[str, list[tuple[Message, bool, str | None]]] = {}
    
    for message in messages:
        if message.media_type not in (MediaType.IMAGE, MediaType.VIDEO):
            continue
            
        primary_location = get_primary_location(message.location)
        success, result = await copy_media_to_location_folder(message, base_folder)
        
        if primary_location not in results:
            results[primary_location] = []
        results[primary_location].append((message, success, result))
    
    return results