from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from src.config import settings

class WhitelistMiddleware(BaseMiddleware):
    """
    Ensures only authorized users can interact with the bot if ALLOWED_USER_IDS is set.
    If unauthorized, provides their Telegram ID to make setup effortless.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        allowed = settings.allowed_user_ids

        # If no whitelist specified, allow all
        if not allowed:
            return await handler(event, data)

        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)

        if user.id not in allowed:
            denied_msg = (
                "⛔ <b>Access Denied</b>\n\n"
                "This is a private self-hosted <b>RelentlessBot</b> instance.\n\n"
                f"Your Telegram User ID is: <code>{user.id}</code>\n\n"
                "To authorize yourself, add this ID to <code>ALLOWED_USER_IDS</code> in your <code>.env</code> file."
            )
            if isinstance(event, Message):
                await event.answer(denied_msg, parse_mode="HTML")
            elif isinstance(event, CallbackQuery):
                await event.answer("Access Denied.", show_alert=True)
            return

        return await handler(event, data)
