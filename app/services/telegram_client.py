from __future__ import annotations

import asyncio
from getpass import getpass
from pathlib import Path
from typing import Any

from telethon import TelegramClient
from telethon.errors import (
    ChannelPrivateError,
    ChatAdminRequiredError,
    InviteHashExpiredError,
    InviteHashInvalidError,
    RPCError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)
from telethon.tl.custom.message import Message
from telethon.tl.types import Channel, Chat, User


class TelegramClientServiceError(RuntimeError):
    """Base service error for Telethon lifecycle or network issues."""


class TelegramEntityUnavailableError(TelegramClientServiceError):
    """Raised when the target exists but is not publicly accessible."""


class TelegramMessageItem:
    """Simple message container returned by the Telethon service."""

    def __init__(self, text: str, date: Any) -> None:
        self.text = text
        self.date = date


class TelegramClientService:
    """Shared Telethon client for lawful public Telegram access."""

    def __init__(self, api_id: int | None, api_hash: str, session_name: str = "robocop_session") -> None:
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self._client: TelegramClient | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Create and authorize a single reusable Telethon client."""

        async with self._lock:
            if self._client is not None and self._client.is_connected():
                return

            if not self.api_id or not self.api_hash:
                raise TelegramClientServiceError(
                    "Не задано TG_API_ID або TG_API_HASH. Додайте їх у .env перед запуском."
                )

            session_path = self._build_session_path(self.session_name)
            client = TelegramClient(str(session_path), self.api_id, self.api_hash)

            try:
                await client.connect()
                if not await client.is_user_authorized():
                    await client.start(
                        phone=self._prompt_phone,
                        password=self._prompt_password,
                        code_callback=self._prompt_code,
                    )
            except Exception as exc:
                await client.disconnect()
                raise TelegramClientServiceError("Не вдалося підключити Telethon-клієнт.") from exc

            self._client = client

    async def stop(self) -> None:
        """Disconnect the shared Telethon client if it is running."""

        async with self._lock:
            if self._client is None:
                return

            await self._client.disconnect()
            self._client = None

    async def resolve_entity(self, target: str):
        """Resolve a public username or link into a Telethon entity or None."""

        client = await self._get_client()
        prepared_target = self._prepare_target(target)

        try:
            return await client.get_entity(prepared_target)
        except (ValueError, UsernameInvalidError, UsernameNotOccupiedError):
            return None
        except (ChannelPrivateError, InviteHashInvalidError, InviteHashExpiredError) as exc:
            raise TelegramEntityUnavailableError("Об’єкт недоступний або не є публічним.") from exc
        except RPCError as exc:
            raise TelegramEntityUnavailableError("Об’єкт недоступний або не є публічним.") from exc
        except OSError as exc:
            raise TelegramClientServiceError("Не вдалося отримати дані з Telegram.") from exc

    async def fetch_messages(self, entity, limit: int) -> list[TelegramMessageItem]:
        """Return recent non-empty text messages for a public entity."""

        client = await self._get_client()
        messages: list[TelegramMessageItem] = []

        try:
            async for message in client.iter_messages(entity, limit=limit):
                if not isinstance(message, Message):
                    continue

                text = (message.message or "").strip()
                if not text:
                    continue

                messages.append(TelegramMessageItem(text=text, date=message.date))
        except (ChannelPrivateError, ChatAdminRequiredError) as exc:
            raise TelegramEntityUnavailableError("Об’єкт недоступний або не є публічним.") from exc
        except RPCError as exc:
            raise TelegramClientServiceError("Не вдалося отримати дані з Telegram.") from exc
        except OSError as exc:
            raise TelegramClientServiceError("Не вдалося отримати дані з Telegram.") from exc

        return messages

    def is_public_entity(self, entity: Any) -> bool:
        """Allow only public Telegram users/channels with a username."""

        if isinstance(entity, Chat):
            return False

        if isinstance(entity, (User, Channel)):
            return bool(getattr(entity, "username", None))

        return bool(getattr(entity, "username", None))

    def build_entity_title(self, entity: Any) -> str | None:
        """Return a readable entity title for the collector."""

        title = getattr(entity, "title", None)
        if isinstance(title, str) and title.strip():
            return title.strip()

        first_name = getattr(entity, "first_name", None)
        last_name = getattr(entity, "last_name", None)
        full_name = " ".join(part for part in [first_name, last_name] if part)
        if full_name.strip():
            return full_name.strip()

        username = getattr(entity, "username", None)
        if username:
            return f"@{username}"

        return None

    async def _get_client(self) -> TelegramClient:
        if self._client is None or not self._client.is_connected():
            await self.start()

        if self._client is None:
            raise TelegramClientServiceError("Telethon-клієнт недоступний.")

        return self._client

    def _prepare_target(self, target: str) -> str:
        value = target.strip()
        value = value.removeprefix("https://").removeprefix("http://")
        value = value.removeprefix("t.me/").removeprefix("www.t.me/")
        value = value.removeprefix("telegram.me/").removeprefix("www.telegram.me/")
        value = value.removeprefix("@")

        path_parts = [part for part in value.split("/") if part]
        if not path_parts:
            return value
        return path_parts[0]

    def _build_session_path(self, session_name: str) -> Path:
        path = Path(session_name)
        if path.is_absolute():
            return path
        return Path.cwd() / path

    def _prompt_phone(self) -> str:
        return input("Введіть номер телефону для авторизації Telethon: ").strip()

    def _prompt_code(self) -> str:
        return input("Введіть код підтвердження Telegram: ").strip()

    def _prompt_password(self) -> str:
        return getpass("Введіть пароль 2FA Telegram: ")
