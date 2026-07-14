from datetime import datetime, timezone

from .models import Message
from .client import connect_client, disconnect_client


async def send_post(
    dest_channel: str,
    message: Message,
    include_image: bool = True,
) -> tuple[str | None, str | None]:
    client = await connect_client()
    try:
        dest_entity = await client.get_entity(dest_channel)

        text_parts = []
        if message.message_text:
            text_parts.append(message.message_text)
        if message.image_text:
            text_parts.append("---\n" + message.image_text)

        caption = "\n\n".join(text_parts) if text_parts else ""

        sent_msg = None
        if include_image and message.media_path and message.media_type.value == "image":
            sent_msg = await client._client.send_file(
                dest_entity,
                file=message.media_path,
                caption=caption if caption else None,
            )
        else:
            if caption:
                sent_msg = await client._client.send_message(
                    dest_entity,
                    message=caption,
                )

        published_link = None
        if sent_msg:
            published_link = client.build_post_link(dest_entity, sent_msg.id)

        return published_link, None
    except Exception as e:
        return None, str(e)
    finally:
        await disconnect_client()


async def publish_messages(
    db,
    source_channel: str,
    dest_channel: str,
    filter_mode: str,
    limit: int | None = None,
    include_image: bool = True,
):
    pending_count = await db.get_unpublished_count(source_channel, filter_mode)
    if pending_count == 0:
        print(f"No unpublished posts to publish for {source_channel}.")
        return 0, 0

    messages = await db.get_unpublished_by_source(source_channel, filter_mode, limit)
    if limit and len(messages) > limit:
        messages = messages[:limit]

    print(f"Found {pending_count} pending post(s) for {source_channel}.")
    print(f"Publishing {len(messages)} post(s) to {dest_channel}.")

    published = 0
    failed = 0

    for i, msg in enumerate(messages, 1):
        link_preview = msg.post_link.split("/")[-1] if msg.post_link else msg.message_id
        print(f"\n[{i}/{len(messages)}] Posting msg {msg.message_id} (source link: {link_preview})...")

        published_link, error = await send_post(
            dest_channel=dest_channel,
            message=msg,
            include_image=include_image,
        )

        if error:
            print(f"  [ERROR] {error}")
            failed += 1
        else:
            print(f"  [OK] {published_link}")
            published += 1
            await db.mark_published(
                channel_id=msg.channel_id,
                message_id=msg.message_id,
                published_link=published_link,
                published_at=datetime.now(timezone.utc).isoformat(),
            )

    return published, failed