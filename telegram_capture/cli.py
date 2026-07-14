import argparse
import asyncio
import sys
import signal
import platform

from .client import connect_client, disconnect_client
from .database import get_database, close_database
from .capture import capture_channel
from .vision import is_ollama_running, extract_text_from_image
from .publisher import publish_messages


async def run(args):
    if args.extract_image_text:
        await extract_image_text(args)
        return

    if args.publish:
        await publish_posts(args)
        return

    db = await get_database()
    try:
        client = await connect_client()
        try:
            me = await client.get_me()
            print(f"Logged in as: {me.first_name} {me.last_name or ''} (@{me.username})")
        except Exception:
            print("Warning: Could not retrieve account info")

        if args.list_channels:
            print("\nYour channels and groups:")
            print("-" * 60)
            dialogs = await client.list_dialogs(limit=100)
            for dtype, title, username, eid in dialogs:
                if dtype in ('Channel', 'Chat'):
                    link = f"@{username}" if username else f"ID: {eid}"
                    print(f"  [{dtype}] {title} ({link})")
            print("-" * 60)
            return

        if not args.channel:
            print("Error: --channel is required (or use --list-channels to see your channels)")
            sys.exit(1)

        captured, skipped = await capture_channel(
            client=client,
            db=db,
            channel_identifier=args.channel,
            limit=args.limit,
            scheduled=args.scheduled,
        )

        total = await db.get_message_count()
        print(f"\nDone. Captured: {captured} | Skipped (duplicates): {skipped} | Total in DB: {total}")
    finally:
        await disconnect_client()
        await close_database()


async def extract_image_text(args):
    if not args.channel:
        print("Error: --extract-image-text requires --channel")
        sys.exit(1)

    print("Checking Ollama status...")
    if not await is_ollama_running():
        print("Ollama is not running at http://localhost:11434")
        response = input("Start Ollama now? Open a terminal and run: ollama serve  [Y/n]: ").strip().lower()
        if response in ("", "y", "yes"):
            print("Please start Ollama in another terminal, then run this command again.")
        else:
            print("Aborted.")
        sys.exit(0)

    db = await get_database()
    try:
        total_pending = await db.get_pending_images_count(args.channel)
        if total_pending == 0:
            print(f"No pending images to process for {args.channel}.")
            return

        messages = await db.get_pending_images(args.channel, limit=args.limit)
        processed = 0
        failed = 0

        print(f"\nFound {total_pending} pending image(s) for {args.channel}.")
        if args.limit and args.limit < len(messages):
            print(f"Processing {len(messages)} (--limit {args.limit}).")
        else:
            print(f"Processing all {len(messages)}.")

        for i, msg in enumerate(messages, 1):
            text_preview = msg.media_path.split("/")[-1] if msg.media_path else msg.message_id
            print(f"\n[{i}/{len(messages)}] Processing message {msg.message_id} ({text_preview})...")

            extracted_text, error = await extract_text_from_image(msg.media_path)

            if error:
                print(f"  [ERROR] {error}")
                failed += 1
            else:
                preview = extracted_text[:80].replace("\n", " ") if extracted_text else ""
                print(f"  [OK] {preview}...")
                processed += 1

            await db.update_image_text(
                msg.channel_id, msg.message_id, extracted_text, error
            )

        print(f"\nDone. Processed: {processed} | Failed: {failed}")
    finally:
        await close_database()


async def publish_posts(args):
    if not args.source_channel:
        print("Error: --publish requires --source-channel")
        sys.exit(1)
    if not args.dest_channel:
        print("Error: --publish requires --dest-channel")
        sys.exit(1)
    if not args.filter_mode:
        print("Error: --publish requires --filter-mode")
        sys.exit(1)
    if args.filter_mode not in ("with_image_text", "with_message_text"):
        print("Error: --filter-mode must be 'with_image_text' or 'with_message_text'")
        sys.exit(1)

    db = await get_database()
    try:
        published, failed = await publish_messages(
            db=db,
            source_channel=args.source_channel,
            dest_channel=args.dest_channel,
            filter_mode=args.filter_mode,
            limit=args.limit,
            include_image=not args.no_image,
        )
        print(f"\nDone. Published: {published} | Failed: {failed}")
    finally:
        await close_database()


def main():
    parser = argparse.ArgumentParser(
        description="Capture Telegram channel messages to SQLite"
    )
    parser.add_argument(
        "--channel",
        help="@username for public channels or invite link for private",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of messages to capture (or images to process/publish)",
    )
    parser.add_argument(
        "--scheduled",
        action="store_true",
        help="Run in scheduled mode: captures messages from yesterday to now",
    )
    parser.add_argument(
        "--list-channels",
        action="store_true",
        help="List all your channels and groups, then exit",
    )
    parser.add_argument(
        "--extract-image-text",
        action="store_true",
        help="Extract text from images in a channel using Ollama vision model",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish posts from database to a destination channel",
    )
    parser.add_argument(
        "--source-channel",
        help="Source channel ID to read posts from (e.g. @somechannel)",
    )
    parser.add_argument(
        "--dest-channel",
        help="Destination channel to publish posts to (e.g. @destchannel)",
    )
    parser.add_argument(
        "--filter-mode",
        choices=["with_image_text", "with_message_text"],
        help="Which posts to publish: 'with_image_text' (images with extracted text) or 'with_message_text' (text-only posts)",
    )
    parser.add_argument(
        "--no-image",
        action="store_true",
        help="Send text only (no image) even for image posts",
    )

    args = parser.parse_args()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if platform.system() != "Windows":
        loop.add_signal_handler(signal.SIGINT, lambda: loop.stop())
        loop.add_signal_handler(signal.SIGTERM, lambda: loop.stop())

    try:
        loop.run_until_complete(run(args))
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        loop.close()