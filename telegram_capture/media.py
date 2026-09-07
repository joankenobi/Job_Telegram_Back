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


def get_location_folder(base_folder: Path, location: str, channel: str) -> Path:
    """Get the folder path for a specific location within the base folder."""
    # Sanitize location name for filesystem
    safe_location = "".join(c for c in location if c.isalnum() or c in (" ", "-", "_")).strip()
    safe_location = safe_location.replace(" ", "_")
    # return base_folder / Path("locations") / safe_location
    return base_folder / Path("locations") / channel.lstrip("@")


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
    location_folder = get_location_folder(base_folder, primary_location, message.channel_id)
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

def list_files(folder: str | Path, pattern: str = "*") -> list[Path]:
    path = Path(folder)
    if not path.exists():
        return []
    return list(path.glob(pattern))

def get_unique_files_list_in_two_files(list_a:list[Path], list_b:list[Path]) -> list[str]:
    set_a = set([f.name for f in list_a])
    set_b = set([f.name for f in list_b])

    print(set_a)

    print("/n/n")

    print(set_b)

    return list(set_a ^ set_b)

async def create_not_classifycated_files(channel:str, compare_folder="locations"):
    try:
        channel_folder = get_channel_folder(channel,None)
        compare_folder = DOWNLOADS_DIR / compare_folder / channel.lstrip("@")

        list_a = list_files(channel_folder, "**/*.jpg")
        list_b = list_files(compare_folder, "**/*.jpg")

        unique_list = get_unique_files_list_in_two_files(list_a, list_b)

        dest_path = DOWNLOADS_DIR / "unclassify" / channel

        dest_path.mkdir(parents=True, exist_ok=True)

        for file in list_a:
            if file.name in unique_list:
                shutil.copy2(file, dest_path)

    finally:
        print("unclassify foles created")

if __name__ == "__main__":
    asyncio.run(
     create_not_classifycated_files("@rrhh_Venezuela")
    )
