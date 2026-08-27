import argparse
import asyncio
import re
import sys
import signal
import platform

from .client import connect_client, disconnect_client
from .database import get_database, close_database
from .capture import capture_channel
from .vision import is_ollama_running, extract_all_text_from_image, extract_contact_info_text
from .publisher import publish_messages
from .text_to_imagen import message_text_to_image


async def run(args):
    if args.extract_image_text:
        await extract_image_text(args)
        return

    if args.publish:
        await publish_posts(args)
        return

    if args.classify_by_location:
        await classify_by_location(args)
        return

    if args.text_to_img:
        await message_text_to_image(args)
        return

    db = await get_database()
    try:
        client = await connect_client()
        try:
            me = await client.get_me()
            print(
                f"Logged in as: {me.first_name} {me.last_name or ''} (@{me.username})"
            )
        except Exception:
            print("Warning: Could not retrieve account info")

        if args.list_channels:
            print("\nYour channels and groups:")
            print("-" * 60)
            dialogs = await client.list_dialogs(limit=100)
            for dtype, title, username, eid in dialogs:
                if dtype in ("Channel", "Chat"):
                    link = f"@{username}" if username else f"ID: {eid}"
                    print(f"  [{dtype}] {title} ({link})")
            print("-" * 60)
            return

        if not args.channel:
            print(
                "Error: --channel is required (or use --list-channels to see your channels)"
            )
            sys.exit(1)

        captured, skipped = await capture_channel(
            client=client,
            db=db,
            channel_identifier=args.channel,
            limit=args.limit,
            scheduled=args.scheduled,
            month=args.month,
        )

        total = await db.get_message_count()
        print(
            f"\nDone. Captured: {captured} | Skipped (duplicates): {skipped} | Total in DB: {total}"
        )
    finally:
        await disconnect_client()
        await close_database()


async def extract_image_text(args):

    # Teléfonos: soporta +58, 0412-, (0212), con espacios, puntos o guiones
    PHONE_PATTERN = r"(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}[\s.-]?\d{3,4}"

    # Correos: el clásico, suficiente para la mayoría de casos
    EMAIL_PATTERN = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"

    if not args.channel:
        print("Error: --extract-image-text requires --channel")
        sys.exit(1)

    print("Checking Ollama status...")
    if not await is_ollama_running():
        print("Ollama is not running at http://localhost:11434")
        response = (
            input("Start Ollama now? Open a terminal and run: ollama serve  [Y/n]: ")
            .strip()
            .lower()
        )
        if response in ("", "y", "yes"):
            print(
                "Please start Ollama in another terminal, then run this command again."
            )
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
            text_preview = (
                msg.media_path.split("/")[-1] if msg.media_path else msg.message_id
            )
            print(
                f"\n[{i}/{len(messages)}] Processing message {msg.message_id} ({text_preview})..."
            )
            while True:
                extracted_text, error = await extract_all_text_from_image(msg.media_path)

                if extracted_text is None:
                    print("extracted_text is none")
                
                if extracted_text is not None:
                    break
                
            phone_numbers = []
            emails = []
            if extracted_text:
                phone_numbers = re.findall(PHONE_PATTERN, extracted_text['imagen_text'])
                emails = re.findall(EMAIL_PATTERN, extracted_text['imagen_text'])
                print(f" extracted_text: {extracted_text}")

            firstItemListExist = lambda x : x[0] if x.__len__() > 0 else None

            if error:
                print(f"  [ERROR] {error}")
                failed += 1
            else:
                preview = (
                    extracted_text['imagen_text'][:80].replace("\n", " ") if extracted_text else ""
                )
                print(f"  [OK] {preview}...")
                print(f" extracted_text: {extracted_text}")
                print(f" Teléfonos: {phone_numbers}")
                print(f" Correos:   {emails}")
                print(f" message_id:   { msg.message_id}")
                processed += 1

            await db.update_info_contact(
                msg.channel_id, msg.message_id, firstItemListExist(phone_numbers), firstItemListExist(emails)
            )
            await db.update_profession_location(
                msg.channel_id, msg.message_id, extracted_text["professions"], extracted_text["locations"]
            )
            await db.update_image_text(
                msg.channel_id, msg.message_id, extracted_text['imagen_text'], error
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

async def classify_by_location(args):
    from .media import classify_media_by_location
    from .config import DOWNLOADS_DIR

    db = await get_database()
    try:
        if args.channel:
            # Single channel
            print(f"Classifying media for channel: {args.channel}")
            messages_with_loc = await db.get_messages_with_location(args.channel, limit=args.limit)
            messages_without_loc = await db.get_messages_without_location(args.channel, limit=args.limit)
            all_messages = messages_with_loc + messages_without_loc
        else:
            # All channels - get all messages with media
            print("Classifying media for all channels...")
            all_messages = await db.get_all_media_messages(limit=args.limit)

        if not all_messages:
            print("No media messages found to classify.")
            return

        print(f"Found {len(all_messages)} media message(s) to classify.")
        
        results = await classify_media_by_location(all_messages, DOWNLOADS_DIR)
        
        total_copied = 0
        total_failed = 0
        for location, items in results.items():
            copied = sum(1 for _, success, _ in items if success)
            failed = sum(1 for _, success, _ in items if not success)
            total_copied += copied
            total_failed += failed
            print(f"  {location}: {copied} copied, {failed} failed")

        print(f"\nDone. Total copied: {total_copied} | Total failed: {total_failed}")
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
        "--month",
        help="Capture messages from a specific month (format: MM-YYYY, e.g. 07-2026)",
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
    parser.add_argument(
        "--classify-by-location",
        action="store_true",
        help="Classify and copy media files into location-based folders within downloads",
    )
    parser.add_argument(
        "--text-to-img",
        action="store_true",
        help="Create images from messages text",
    )

    args = parser.parse_args()

    if args.month:
        if not re.match(r"^\d{2}-\d{4}$", args.month):
            print(
                f"Error: --month must be in MM-YYYY format (e.g. 07-2026), got: '{args.month}'"
            )
            sys.exit(1)
        month_num = int(args.month.split("-")[0])
        if month_num < 1 or month_num > 12:
            print(f"Error: --month month number must be 01-12, got: {month_num}")
            sys.exit(1)

    if args.month and args.scheduled:
        print("Error: --month and --scheduled are mutually exclusive")
        sys.exit(1)

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
