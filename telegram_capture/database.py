import aiosqlite
from pathlib import Path
import asyncio

from .config import DATABASE_PATH
from .models import Message


CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id      TEXT    NOT NULL,
    channel_title   TEXT,
    message_id      INTEGER NOT NULL,
    date            TEXT    NOT NULL,
    message_text    TEXT,
    media_type      TEXT    NOT NULL,
    media_path      TEXT,
    post_link       TEXT,
    raw_data        TEXT,
    captured_at     TEXT    DEFAULT (datetime('now')),
    image_text      TEXT,
    ollama_error    TEXT,
    published       INTEGER DEFAULT 0,
    published_at    TEXT,
    published_link  TEXT,
    email TEXT,
    phone_number TEXT,
    UNIQUE(channel_id, message_id)
);
CREATE INDEX IF NOT EXISTS idx_channel_msg ON messages(channel_id, message_id);
CREATE INDEX IF NOT EXISTS idx_channel ON messages(channel_id);
"""


class Database:
    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        await self._conn.executescript(CREATE_TABLE)
        await self._conn.commit()
        await self.ensure_vision_columns()
        await self.ensure_publish_columns()
        await self.ensure_contact_columns()

    async def ensure_vision_columns(self):
        for col_sql in [
            "ALTER TABLE messages ADD COLUMN image_text TEXT",
            "ALTER TABLE messages ADD COLUMN ollama_error TEXT",
        ]:
            try:
                await self._conn.execute(col_sql)
                await self._conn.commit()
            except aiosqlite.OperationalError:
                pass

    async def ensure_contact_columns(self):
        for col_sql in [
            "ALTER TABLE messages ADD COLUMN email TEXT",
            "ALTER TABLE messages ADD COLUMN phone_number TEXT",
        ]:
            try:
                await self._conn.execute(col_sql)
                await self._conn.commit()
            except aiosqlite.OperationalError:
                pass

    async def ensure_publish_columns(self):
        for col_sql in [
            "ALTER TABLE messages ADD COLUMN published INTEGER DEFAULT 0",
            "ALTER TABLE messages ADD COLUMN published_at TEXT",
            "ALTER TABLE messages ADD COLUMN published_link TEXT",
        ]:
            try:
                await self._conn.execute(col_sql)
                await self._conn.commit()
            except aiosqlite.OperationalError:
                pass

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def insert_message(self, message: Message) -> bool:
        if not self._conn:
            raise RuntimeError("Database not connected")
        try:
            await self._conn.execute(
                """
                INSERT INTO messages (
                    channel_id, channel_title, message_id, date,
                    message_text, media_type, media_path, post_link, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                message.to_db_tuple(),
            )
            await self._conn.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def message_exists(self, channel_id: str, message_id: int) -> bool:
        if not self._conn:
            raise RuntimeError("Database not connected")
        cursor = await self._conn.execute(
            "SELECT 1 FROM messages WHERE channel_id = ? AND message_id = ?",
            (channel_id, message_id),
        )
        row = await cursor.fetchone()
        return row is not None

    async def get_channel_messages(
        self, channel_id: str, limit: int | None = None
    ):
        if not self._conn:
            raise RuntimeError("Database not connected")
        query = "SELECT * FROM messages WHERE channel_id = ? ORDER BY date DESC"
        params: list = [channel_id]
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        cursor = await self._conn.execute(query, params)
        rows = await cursor.fetchall()
        return [Message.from_row(row) for row in rows]

    async def get_message_count(self, channel_id: str | None = None) -> int:
        if not self._conn:
            raise RuntimeError("Database not connected")
        if channel_id:
            cursor = await self._conn.execute(
                "SELECT COUNT(*) FROM messages WHERE channel_id = ?", (channel_id,)
            )
        else:
            cursor = await self._conn.execute("SELECT COUNT(*) FROM messages")
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def update_image_text(
        self,
        channel_id: str,
        message_id: int,
        image_text: str | None,
        ollama_error: str | None,
    ):
        if not self._conn:
            raise RuntimeError("Database not connected")
        await self._conn.execute(
            "UPDATE messages SET image_text = ?, ollama_error = ? "
            "WHERE channel_id = ? AND message_id = ?",
            (image_text, ollama_error, channel_id, message_id),
        )
        await self._conn.commit()

    async def update_info_contact(
        self,
        channel_id: str,
        message_id: int,
        phone_number: str | None,
        email: str | None,
    ):
        if not self._conn:
            raise RuntimeError("Database not connected")
        await self._conn.execute(
            "UPDATE messages SET phone_number = ?, email = ?"
            "WHERE channel_id = ? AND message_id = ?",
            (phone_number, email, channel_id, message_id),
        )
        await self._conn.commit()

    async def get_pending_images(
        self, channel_id: str, limit: int | None = None
    ) -> list[Message]:
        if not self._conn:
            raise RuntimeError("Database not connected")
        query = (
            "SELECT * FROM messages WHERE channel_id = ? "
            "AND media_type = 'image' "
            "AND (image_text IS NULL OR image_text = '') "
            "ORDER BY date ASC"
        )
        params: list = [channel_id]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        cursor = await self._conn.execute(query, params)
        rows = await cursor.fetchall()
        return [Message.from_row(row) for row in rows]

    async def get_pending_images_count(self, channel_id: str) -> int:
        if not self._conn:
            raise RuntimeError("Database not connected")
        cursor = await self._conn.execute(
            "SELECT COUNT(*) FROM messages WHERE channel_id = ? "
            "AND media_type = 'image' "
            "AND (image_text IS NULL OR image_text = '')",
            (channel_id,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def get_unpublished_by_source(
        self,
        source_channel: str,
        filter_mode: str,
        limit: int | None = None,
    ) -> list[Message]:
        if not self._conn:
            raise RuntimeError("Database not connected")

        if filter_mode == "with_image_text":
            where = (
                "channel_id = ? "
                "AND media_type = 'image' "
                "AND image_text IS NOT NULL "
                "AND image_text != '' "
                "AND published = 0"
            )
        elif filter_mode == "with_message_text":
            where = (
                "channel_id = ? "
                "AND message_text IS NOT NULL "
                "AND message_text != '' "
                "AND published = 0"
            )
        else:
            raise ValueError(f"Unknown filter_mode: {filter_mode}")

        query = f"SELECT * FROM messages WHERE {where} ORDER BY date ASC"
        params: list = [source_channel]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        cursor = await self._conn.execute(query, params)
        rows = await cursor.fetchall()
        return [Message.from_row(row) for row in rows]

    async def get_unpublished_count(self, source_channel: str, filter_mode: str) -> int:
        if not self._conn:
            raise RuntimeError("Database not connected")

        if filter_mode == "with_image_text":
            where = (
                "channel_id = ? "
                "AND media_type = 'image' "
                "AND image_text IS NOT NULL "
                "AND image_text != '' "
                "AND published = 0"
            )
        elif filter_mode == "with_message_text":
            where = (
                "channel_id = ? "
                "AND message_text IS NOT NULL "
                "AND message_text != '' "
                "AND published = 0"
            )
        else:
            raise ValueError(f"Unknown filter_mode: {filter_mode}")

        cursor = await self._conn.execute(
            f"SELECT COUNT(*) FROM messages WHERE {where}",
            (source_channel,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def mark_published(
        self,
        channel_id: str,
        message_id: int,
        published_link: str,
        published_at: str,
    ):
        if not self._conn:
            raise RuntimeError("Database not connected")
        await self._conn.execute(
            "UPDATE messages SET published = 1, published_link = ?, published_at = ? "
            "WHERE channel_id = ? AND message_id = ?",
            (published_link, published_at, channel_id, message_id),
        )
        await self._conn.commit()


_db_instance: Database | None = None
_db_lock = asyncio.Lock()


async def get_database() -> Database:
    global _db_instance
    async with _db_lock:
        if _db_instance is None:
            _db_instance = Database()
            await _db_instance.connect()
        return _db_instance


async def close_database():
    global _db_instance
    async with _db_lock:
        if _db_instance:
            await _db_instance.close()
            _db_instance = None