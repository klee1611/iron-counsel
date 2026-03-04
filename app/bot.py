from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.firestore_client import append_message, load_history
from app.rag import answer

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"

WELCOME_MESSAGE = (
    "⚔️ *The Iron Counsel* has been summoned.\n\n"
    "I have survived the Red Wedding, the Purple Wedding, and the inexplicable "
    "cancellation of *Winds of Winter*. Now I am inexplicably here — in your century — "
    "to advise you on whatever trivial catastrophe you face.\n\n"
    "Bring me your petty disputes, your career dilemmas, your impossible group-chat "
    "conflicts. I shall treat them all as matters of dynastic consequence.\n\n"
    "_Valar Morghulis. What troubles the realm?_"
)

UNAUTHORIZED_MESSAGE = "⛔ You are not permitted to consult the maester."


def _is_authorized(user_id: int) -> bool:
    """Return True if the user is allowed. An empty allowlist permits everyone."""
    allowed = settings.allowed_user_id_list
    return not allowed or user_id in allowed


async def handle_update(update: dict) -> None:
    """Process a single Telegram Update object."""
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat_id: int = message["chat"]["id"]
    user_id: int = message.get("from", {}).get("id", chat_id)
    text: str = message.get("text", "").strip()

    if not _is_authorized(user_id):
        await send_message(chat_id, UNAUTHORIZED_MESSAGE)
        return

    if not text:
        return

    if text.startswith("/start"):
        await send_message(chat_id, WELCOME_MESSAGE, parse_mode="Markdown")
        return

    if text.startswith("/"):
        # Ignore other commands
        return

    # Indicate the bot is typing
    await send_chat_action(chat_id, "typing")

    try:
        history = await load_history(chat_id)
        response_text = await answer(text, history)

        # Persist both turns
        await append_message(chat_id, "user", text)
        await append_message(chat_id, "assistant", response_text)

        await send_message(chat_id, response_text)

    except Exception as exc:
        logger.exception("Error handling message from chat_id=%s", chat_id)
        await send_message(
            chat_id,
            "⚠️ The ravens have gone astray. Please try again in a moment.",
        )


# ---------------------------------------------------------------------------
# Telegram Bot API helpers
# ---------------------------------------------------------------------------

def _api_url(method: str) -> str:
    base = TELEGRAM_API_BASE.format(token=settings.telegram_token)
    return f"{base}/{method}"


async def send_message(
    chat_id: int,
    text: str,
    parse_mode: str | None = None,
) -> None:
    payload: dict = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(_api_url("sendMessage"), json=payload)
        if resp.status_code != 200:
            logger.warning("sendMessage failed: %s %s", resp.status_code, resp.text)


async def send_chat_action(chat_id: int, action: str = "typing") -> None:
    async with httpx.AsyncClient(timeout=5) as client:
        await client.post(
            _api_url("sendChatAction"),
            json={"chat_id": chat_id, "action": action},
        )
