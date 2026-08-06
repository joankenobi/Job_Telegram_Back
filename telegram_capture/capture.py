import calendar
import json
import re
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


def get_month_range(month_str: str) -> tuple[datetime, datetime]:
    match = re.match(r'^(\d{2})-(\d{4})$', month_str)
    if not match:
        raise ValueError(
            f"Invalid month format: '{month_str}'. Expected 'MM-YYYY' (e.g. '07-2026')"
        )
    month_num = int(match.group(1))
    year = int(match.group(2))
    if month_num < 1 or month_num > 12:
        raise ValueError(f"Invalid month number: {month_num}. Must be 01-12."
        )
    last_day = calendar.monthrange(year, month_num)[1]
    start = datetime(year, month_num, 1, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(year, month_num, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


async def capture_channel(
    client: TelegramClientWrapper,
    db: Database,
    channel_identifier: str,
    limit: int | None = None,
    scheduled: bool = False,
    month: str | None = None,
):
    entity = await client.get_entity(channel_identifier)
    channel_id:str = client.get_channel_id_str(entity)
    channel_title=getattr(entity, "title", None),

    if month:
        start_date, end_date = get_month_range(month)
    else:
        start_date, end_date = get_yesterday_range()

    captured = 0
    skipped = 0

    # When using --month, don't pass limit to iter_messages (it limits total
    # fetched messages from the API, not captured ones). Apply limit inside
    # the loop instead so we iterate far enough back to reach the target month.
    iter_limit = None if month else limit

    async for telethon_message in client.iter_messages(
        entity, limit=iter_limit
    ):
        telethon_message: TelethonMessage
        print(telethon_message.to_json())
        if telethon_message.date < start_date:
            if not month and telethon_message.date < start_date - timedelta(days=7):
                break
            continue
        if telethon_message.date > end_date:
            continue

        # Apply limit to captured count when using --month
        if month and limit and captured >= limit:
            break

        if await db.message_exists(
            channel_id, telethon_message.id
        ):
            skipped += 1
            continue

        media_path, media_type = await download_media(
            telethon_message,
            channel_id,
            getattr(entity, "title", None),
        )

        post_link = client.build_post_link(entity, telethon_message.id)

        raw_data = json.dumps(
            telethon_message.to_dict(),
            default=str,
            ensure_ascii=False,
        )

        msg = Message(
            channel_id=channel_id,
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