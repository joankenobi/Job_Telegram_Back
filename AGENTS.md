# Telegram Chat Capture - Agent Instructions

This document helps AI coding agents understand the codebase and be immediately productive.

## Project Overview

A Python tool to capture messages, images, and videos from Telegram channels/groups using Telethon (user account). Stores data in SQLite with local file downloads. Supports Ollama vision for image text extraction and publishing posts to destination channels.

## Key Commands

```bash
# Setup
cd telegram_capture
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env  # Edit with TG_API_ID, TG_API_HASH, TG_SESSION

# Run capture
.\venv\Scripts\python.exe run.py --channel "@channelname"
.\venv\Scripts\python.exe run.py --channel "@channelname" --scheduled
.\venv\Scripts\python.exe run.py --list-channels

# Extract text from images (requires Ollama with gemma4:e4b)
.\venv\Scripts\python.exe run.py --extract-image-text --channel "@channelname"

# Publish posts to another channel
.\venv\Scripts\python.exe run.py --publish --source-channel "@source" --dest-channel "@dest" --filter-mode with_image_text
```

## Architecture

```
telegram_capture/
├── run.py                    # Entry point
├── telegram_capture/
│   ├── cli.py                # argparse, command routing
│   ├── config.py             # Env vars, paths
│   ├── models.py             # Message dataclass, MediaType enum
│   ├── database.py           # SQLite CRUD (aiosqlite), singleton pattern
│   ├── client.py             # Telethon wrapper, link building
│   ├── media.py              # Media download logic
│   ├── capture.py            # Core capture orchestration
│   ├── vision.py             # Ollama image-to-text extraction
│   └── publisher.py          # Publish posts to destination channel
├── data/capture.db           # SQLite database (auto-created)
├── downloads/                # Media files (auto-created)
└── requirements.txt
```

## Core Patterns

### Async Singleton Services
- `Database` and `TelegramClientWrapper` use module-level singletons with async locks
- Access via `get_database()` and `connect_client()` / `get_client()`
- Always `await close_database()` and `await disconnect_client()` in finally blocks

### Date Filtering (capture.py)
- Default: captures messages from **yesterday 00:00 UTC to now**
- `--scheduled` flag enables this mode for cron/Task Scheduler
- Messages older than 7 days before start_date break the iteration loop

### Deduplication
- Unique constraint on `(channel_id, message_id)` in SQLite
- `message_exists()` check before insert
- `insert_message()` returns `False` on IntegrityError (duplicate)

### Media Paths
- Public: `downloads/{channel_username}/{YYYYMMDD}/{message_id}_{YYYYMMDD}.{ext}`
- Private: `downloads/private_{channel_title}/{YYYYMMDD}/{message_id}_{YYYYMMDD}.{ext}`
- `get_channel_folder()` in config.py handles the base folder; date subfolder created in `media.py`

### Post Links
- Public: `https://t.me/{username}/{message_id}`
- Private: `https://t.me/c/{peer_id.channel_id}/{message_id}`

## Database Schema

```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL,
    channel_title TEXT,
    message_id INTEGER NOT NULL,
    date TEXT NOT NULL,           -- ISO datetime
    message_text TEXT,
    media_type TEXT NOT NULL,     -- 'image', 'video', 'none'
    media_path TEXT,
    post_link TEXT,
    raw_data TEXT,                -- Full JSON backup
    captured_at TEXT DEFAULT (datetime('now')),
    image_text TEXT,              -- Ollama extracted text
    ollama_error TEXT,            -- Ollama error if failed
    published INTEGER DEFAULT 0,  -- 1 if published
    published_at TEXT,            -- ISO timestamp
    published_link TEXT,          -- Link to published post
    UNIQUE(channel_id, message_id)
);
```

## Key Files to Understand

| File | Purpose |
|------|---------|
| `cli.py` | Command routing, argument parsing, main async loop |
| `capture.py` | Core capture logic, date filtering, deduplication |
| `database.py` | All SQLite operations, schema migrations |
| `client.py` | Telethon wrapper, entity resolution, link building |
| `media.py` | Media type detection, download, file naming |
| `vision.py` | Ollama HTTP client for image text extraction |
| `publisher.py` | Send posts to destination channel with tracking |

## Common Development Tasks

### Adding a new CLI command
1. Add argument in `cli.py` `main()`
2. Add handler function in `cli.py`
3. Call from `run()` with early return pattern

### Adding a database column
1. Add to `CREATE_TABLE` in `database.py`
2. Add migration in `ensure_*_columns()` methods
3. Update `Message` dataclass in `models.py`
4. Update `to_db_tuple()` and `from_row()`

### Modifying capture logic
- Main logic in `capture_channel()` in `capture.py`
- Date range: `get_yesterday_range()` returns (start, end)
- Iteration: `client.iter_messages(entity, limit=limit)`

### Working with media
- `get_media_type()` detects image/video/none
- `download_media()` handles download with deduplication
- File naming: `{message_id}_{YYYYMMDD}.{ext}`

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TG_API_ID` | Yes | - | Telegram app ID |
| `TG_API_HASH` | Yes | - | Telegram app hash |
| `TG_SESSION` | No | `telegram_capture` | Session file name |
| `TG_PHONE` | No | - | Phone for auto-login |

## Testing

No formal test suite. Manual testing via CLI:
```bash
# List channels to verify auth
.\venv\Scripts\python.exe run.py --list-channels

# Capture with limit for quick test
.\venv\Scripts\python.exe run.py --channel "@channel" --limit 5
```

## Potential Pitfalls

1. **Windows event loop**: Uses `asyncio.new_event_loop()` explicitly in `cli.py`
2. **Telethon session**: First run requires interactive login (phone/code)
3. **Ollama**: Must be running locally at `http://localhost:11434` with `gemma4:e4b` model
4. **Private channels**: Use invite link `https://t.me/+/hash` format
5. **Rate limits**: Telethon handles flood waits automatically
6. **Timezone**: All dates stored as UTC ISO strings

## Related Documentation

- [README.md](README.md) - Full usage documentation
- [plan.md](plan.md) - Project plan and schema details