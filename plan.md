# Telegram Chat Capture - Project Plan

## Overview

A Python tool to capture messages, images, and videos from any Telegram channel/group you belong to. Stores everything in SQLite with local file downloads. Uses Telethon with your user account.

---

## Project Structure

```
telegram_capture/
├── telegram_capture/          # Main package
│   ├── __init__.py
│   ├── __main__.py            # Entry point
│   ├── config.py               # Env vars: TG_API_ID, TG_API_HASH, TG_SESSION
│   ├── models.py               # Message dataclass
│   ├── database.py             # SQLite CRUD (aiosqlite)
│   ├── client.py               # Telethon session, link builder
│   ├── media.py               # Media download to structured path
│   ├── capture.py             # Core: date filter + deduplicate
│   └── cli.py                 # argparse interface
├── downloads/                  # Auto-created, channel folders inside
│   ├── {channel_username}/
│   │   └── {message_id}_{YYYYMMDD}.{ext}
│   └── private_{channel_title}/
├── data/
│   └── capture.db             # SQLite database
├── venv/                      # Python virtual environment
├── requirements.txt
├── .env.example
└── README.md
```

---

## Configuration

| Variable | Source | Description |
|----------|--------|-------------|
| `TG_API_ID` | Env | Telegram app ID (from my.telegram.org) |
| `TG_API_HASH` | Env | Telegram app hash |
| `TG_SESSION` | Env | Session name (default: `telegram_capture`) |

---

## Database Schema

**Table: `messages`**

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `channel_id` | TEXT | @username or numeric chat ID |
| `channel_title` | TEXT | Full channel name |
| `message_id` | INTEGER | Telegram message ID |
| `date` | TEXT | ISO datetime of original post |
| `message_text` | TEXT | Message content |
| `media_type` | TEXT | `image`, `video`, or `none` |
| `media_path` | TEXT | Local path to downloaded file |
| `post_link` | TEXT | Full t.me URL |
| `raw_data` | TEXT | JSON serialized full message |
| `captured_at` | TEXT | When captured (default now) |

**Unique constraint:** `(channel_id, message_id)` — prevents duplicates

---

## Media Path Structure

```
Public channel:  downloads/{channel_username}/{YYYYMMDD}/{message_id}_{YYYYMMDD}.{ext}
Private channel: downloads/private_{channel_title}/{YYYYMMDD}/{message_id}_{YYYYMMDD}.{ext}

Examples:
  downloads/somechannel/20240528/12345_20240528.jpg
  downloads/private_MyChannel/20240529/789_20240529.png
```

---

## Date Format

Filename format: `YYYYMMDD` (e.g., `20240528`)

---

## Post Link Generation

- **Public:** `https://t.me/{channel_username}/{message_id}`
- **Private:** `https://t.me/c/{channel_numeric_id}/{message_id}`

---

## Execution Modes

### One-time Capture

Captures messages from yesterday 00:00:00 to now.

```bash
python -m telegram_capture --channel "@username_or_invite_link"
```

### With Limit

```bash
python -m telegram_capture --channel "@username" --limit 100
```

### Scheduled Mode

For use with cron/Task Scheduler. Always captures yesterday→now range (idempotent).

```bash
python -m telegram_capture --channel "@username" --scheduled
```

---

## Duplicate Handling

- Messages already in DB (by `channel_id + message_id`) are skipped
- Re-runs are safe and will not re-download media
- Uses `UNIQUE` constraint in SQLite for safety

---

## Dependencies

```
telethon>=1.35.0
aiosqlite>=0.20.0
python-dateutil>=2.9.0
pydantic>=2.9.0
python-dotenv>=1.0.1
```

---

## Setup Instructions

### 1. Get Telegram API Credentials

1. Visit https://my.telegram.org
2. Create a new application
3. Copy `api_id` and `api_hash`

### 2. Install

```bash
cd telegram_capture
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure

```bash
copy .env.example .env
```

Edit `.env`:
```
TG_API_ID=12345
TG_API_HASH=your_api_hash_here
TG_SESSION=telegram_capture
```

### 4. Run

```bash
# First run will prompt for phone number to authenticate
.\venv\Scripts\python.exe -m telegram_capture --channel "@yourchannel"
```

---

## Scheduling

### Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: Daily (or your preference)
4. Action: Start a program
   - Program: `C:\path\to\telegram_capture\venv\Scripts\python.exe`
   - Arguments: `-m telegram_capture --channel "@somechannel" --scheduled`
   - Start in: `C:\path\to\telegram_capture`

### Linux/macOS Cron

```cron
0 1 * * * cd /path/to/telegram_capture && ./venv/bin/python -m telegram_capture --channel "@somechannel" --scheduled
```

---

## Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `config.py` | Load env vars, paths |
| `models.py` | Message dataclass, serialization |
| `database.py` | Async SQLite CRUD, singleton connection |
| `client.py` | Telethon connection, entity resolution, link building |
| `media.py` | Detect media type, download to structured path |
| `capture.py` | Date range filter, iterate messages, orchestrate |
| `cli.py` | argparse, run loop |

---

## Implementation Status

- [x] Project structure and requirements.txt
- [x] config.py, models.py, database.py
- [x] client.py, media.py, capture.py
- [x] cli.py and __main__.py
- [x] .env.example and README.md
- [x] venv created and dependencies installed