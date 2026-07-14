import json
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse as parse_date

from telethon.types import Message as TelethonMessage

from .client import TelegramClientWrapper
from .database import Database
from .models import Message, MediaType
from .media import download_media


def get_yesterday_range() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    yesterday_start = datetime.combine(
        now.date() - timedelta(days=1),
        datetime.min.time(),
        tzinfo=timezone.utc
    )
    return yesterday_start, now
    return yesterday_start, now


async def capture_channel(
    client: TelegramClientWrapper,
    db: Database,
    channel_identifier: str,
    limit: int | None = None,
    scheduled: bool = False,
):
    entity = await client.get_entity(channel_identifier)

    start_date, end_date = get_yesterday_range()

    captured = 0
    skipped = 0

    async for telethon_message in client.iter_messages(
        entity, limit=limit
    ):
        if telethon_message.date < start_date:
            if telethon_message.date < start_date - timedelta(days=7):
                break
            continue
        if telethon_message.date > end_date:
            continue

        if await db.message_exists(
            client.get_channel_id_str(entity), telethon_message.id
        ):
            skipped += 1
            continue

        media_path, media_type = await download_media(
            telethon_message,
            client.get_channel_id_str(entity),
            getattr(entity, "title", None),
        )

        post_link = client.build_post_link(entity, telethon_message.id)

        raw_data = json.dumps(
            telethon_message.to_dict(),
            default=str,
            ensure_ascii=False,
        )

        msg = Message(
            channel_id=client.get_channel_id_str(entity),
            channel_title=getattr(entity, "title", None),
            message_id=telethon_message.id,
            date=telethon_message.date,
            message_text=telethon_message.text or "",
            media_type=media_type,
            media_path=media_path,
            post_link=post_link,
            raw_data=raw_data,
        )

        if await db.insert_message(msg):
            captured += 1
            print(
                f"[+] #{captured} saved: {post_link} | {media_type.value} | {telethon_message.date.strftime('%Y-%m-%d %H:%M')}"
            )
        else:
            skipped += 1

    return captured, skipped