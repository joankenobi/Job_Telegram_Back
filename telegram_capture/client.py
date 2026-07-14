from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.types import Channel, Chat
import os

from .config import API_ID, API_HASH, SESSION_NAME


class TelegramClientWrapper:
    def __init__(self, session_name: str = SESSION_NAME):
        self.session_name = session_name
        self._client: TelegramClient | None = None

    async def connect(self):
        phone = os.getenv("TG_PHONE")
        self._client = TelegramClient(self.session_name, API_ID, API_HASH)
        if phone:
            await self._client.start(phone=phone)
        else:
            await self._client.start()

    async def disconnect(self):
        if self._client:
            await self._client.disconnect()
            self._client = None

    async def get_me(self):
        if not self._client:
            raise RuntimeError("Client not connected")
        return await self._client.get_me()

    async def list_dialogs(self, limit: int = 50):
        if not self._client:
            raise RuntimeError("Client not connected")
        dialogs = []
        async for dialog in self._client.iter_dialogs(limit=limit):
            entity = dialog.entity
            entity_type = type(entity).__name__
            title = getattr(entity, 'title', None) or getattr(entity, 'first_name', None) or 'Unknown'
            username = getattr(entity, 'username', None) or ''
            dialogs.append((entity_type, title, username, entity.id))
        return dialogs

    async def get_entity(self, channel_identifier: str):
        if not self._client:
            raise RuntimeError("Client not connected")

        entity = await self._client.get_entity(channel_identifier)
        return entity

    def iter_messages(
        self,
        entity,
        limit: int | None = None,
        offset_date=None,
        reverse: bool = False,
    ):
        if not self._client:
            raise RuntimeError("Client not connected")
        return self._client.iter_messages(
            entity, limit=limit, offset_date=offset_date, reverse=reverse
        )

    def build_post_link(self, entity, message_id: int) -> str:
        if hasattr(entity, "username") and entity.username:
            return f"https://t.me/{entity.username}/{message_id}"
        peer_id = getattr(entity, "peer_id", None)
        if peer_id:
            return f"https://t.me/c/{peer_id.channel_id}/{message_id}"
        return f"https://t.me/c/{entity.id}/{message_id}"

    def get_channel_id_str(self, entity) -> str:
        if hasattr(entity, "username") and entity.username:
            return f"@{entity.username}"
        if hasattr(entity, "left") and not hasattr(entity, "username"):
            return str(entity.id)
        return str(entity.id)


_client_instance: TelegramClientWrapper | None = None


def get_client() -> TelegramClientWrapper:
    global _client_instance
    if _client_instance is None:
        _client_instance = TelegramClientWrapper()
    return _client_instance


async def connect_client():
    client = get_client()
    await client.connect()
    return client


async def disconnect_client():
    global _client_instance
    if _client_instance:
        await _client_instance.disconnect()
        _client_instance = None