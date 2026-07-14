# Telegram Chat Capture

Capture messages, images, and videos from any Telegram channel/group you belong to. Stores everything in SQLite with local file downloads. Supports extracting text from images using Ollama local AI.

## Features

- Captures messages from yesterday to now by default
- Downloads images and videos to structured local paths
- Works with both public (@username) and private channels
- Idempotent: duplicates are skipped safely
- Scheduled mode for recurring captures
- Extracts text from images using Ollama vision model (gemma4:e4b)
- Publishes posts from database to a destination channel (with tracking)

## Requirements

- Python 3.11+
- Telegram API credentials from https://my.telegram.org
- Ollama (optional, only needed for `--extract-image-text`)
  - Model: `gemma4:e4b` (run `ollama pull gemma4:e4b`)

## Setup

### 1. Install dependencies

```bash
cd telegram_capture
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
copy .env.example .env
```

Edit `.env`:
```
TG_API_ID=12345
TG_API_HASH=your_api_hash_here
TG_SESSION=telegram_capture
```

To get your API credentials:
1. Visit https://my.telegram.org
2. Create a new application
3. Copy the `api_id` and `api_hash`

### 3. (Optional) Set up Ollama for image text extraction

```bash
ollama pull gemma4:e4b
ollama serve
```

## Usage

### Capture messages from a channel

```bash
.\venv\Scripts\python.exe run.py --channel "@somechannel"
```

```bash
.\venv\Scripts\python.exe run.py --channel "@rrhh_Venezuela"
```

### List your channels and groups

```bash
.\venv\Scripts\python.exe run.py --list-channels
```

### With limit

```bash
.\venv\Scripts\python.exe run.py --channel "@somechannel" --limit 100
```

### Private channel

```bash
.\venv\Scripts\python.exe run.py --channel "https://t.me/+/invite_link_hash"
```

### Scheduled mode (for cron/Task Scheduler)

```bash
.\venv\Scripts\python.exe run.py --channel "@somechannel" --scheduled
```

### Extract text from images using Ollama

Requires Ollama running with `gemma4:e4b` model. Processes all images in a channel that don't yet have extracted text.

```bash
.\venv\Scripts\python.exe run.py --extract-image-text --channel "@somechannel"
```

With a limit (process only N images):

```bash
.\venv\Scripts\python.exe run.py --extract-image-text --channel "@somechannel" --limit 10
```

If Ollama is not running, you will be prompted to start it.

### Publish posts to a channel

Reads posts from the database and sends them to a destination channel. Uses your user account. You must be a member/admin of the destination channel.

**Post images with extracted text** (posts that have `image_text`):
```bash
.\venv\Scripts\python.exe run.py --publish --source-channel "@source" --dest-channel "@dest" --filter-mode with_image_text
```

**Post text-only messages** (posts that have `message_text`):
```bash
.\venv\Scripts\python.exe run.py --publish --source-channel "@source" --dest-channel "@dest" --filter-mode with_message_text
```

With a limit:
```bash
.\venv\Scripts\python.exe run.py --publish --source-channel "@source" --dest-channel "@dest" --filter-mode with_image_text --limit 10
```

Send text only (no image attachment):
```bash
.\venv\Scripts\python.exe run.py --publish --source-channel "@source" --dest-channel "@dest" --filter-mode with_image_text --no-image
```
```bash
.\venv\Scripts\python.exe run.py --publish --source-channel "@rrhh_Venezuela" --dest-channel "@RGHXBOX" --filter-mode with_image_text --no-image
```

> **Note:** `--publish` tracks published posts automatically. Already-published posts are skipped. To re-publish, edit the `published` column in the database.

## Project Structure

```
telegram_capture/
├── telegram_capture/          # Main package
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py              # Environment configuration
│   ├── models.py              # Message data model
│   ├── database.py            # SQLite operations
│   ├── client.py              # Telegram client wrapper
│   ├── media.py               # Media download logic
│   ├── capture.py             # Core capture orchestration
│   ├── vision.py              # Ollama image-to-text extraction
│   ├── publisher.py           # Publish posts to Telegram channels
│   └── cli.py                 # CLI interface
├── downloads/                  # Downloaded media (auto-created)
│   ├── somechannel/
│   │   ├── 12345_20240528.jpg
│   └── private_MyChannel/
├── data/
│   └── capture.db             # SQLite database (auto-created)
├── venv/                      # Virtual environment
├── run.py                     # Entry point script
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Database Schema

```sql
CREATE TABLE messages (
    id              INTEGER PRIMARY KEY,
    channel_id      TEXT NOT NULL,
    channel_title   TEXT,
    message_id      INTEGER NOT NULL,
    date            TEXT NOT NULL,
    message_text    TEXT,
    media_type      TEXT,       -- 'image', 'video', 'none'
    media_path      TEXT,       -- local path to file
    post_link       TEXT,       -- https://t.me/...
    raw_data        TEXT,       -- full JSON backup
    captured_at     TEXT DEFAULT (datetime('now')),
    image_text      TEXT,       -- extracted text from image (via Ollama)
    ollama_error    TEXT,       -- Ollama error message if extraction failed
    published       INTEGER DEFAULT 0,  -- 1 if already published
    published_at    TEXT,       -- ISO timestamp when published
    published_link  TEXT,       -- link to published post
    UNIQUE(channel_id, message_id)
);
```

## Media Path Structure

```
Public:   downloads/{channel_username}/{YYYYMMDD}/{message_id}_{YYYYMMDD}.{ext}
Private:  downloads/private_{channel_title}/{YYYYMMDD}/{message_id}_{YYYYMMDD}.{ext}

Examples:
  downloads/somechannel/20240528/12345_20240528.jpg
  downloads/private_MyChannel/20240529/789_20240529.png
```

## Schedule Recurring Captures

### Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: Daily (or your preference)
4. Action: Start a program
   - Program: `C:\path\to\telegram_capture\venv\Scripts\python.exe`
   - Arguments: `run.py --channel "@somechannel" --scheduled`
   - Start in: `C:\path\to\telegram_capture`

### Linux/macOS Cron

```cron
0 1 * * * cd /path/to/telegram_capture && ./venv/bin/python run.py --channel "@somechannel" --scheduled
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TG_API_ID` | Yes | - | Telegram API ID from my.telegram.org |
| `TG_API_HASH` | Yes | - | Telegram API hash |
| `TG_SESSION` | No | `telegram_capture` | Session file name |
| `TG_PHONE` | No | - | Phone number for auth (with country code) |

## Dependencies

```
telethon>=1.35.0
aiosqlite>=0.20.0
python-dateutil>=2.9.0
pydantic>=2.9.0
python-dotenv>=1.0.1
httpx>=0.27.0
```