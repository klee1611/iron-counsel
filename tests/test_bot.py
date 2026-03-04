"""Tests for the Telegram update handler in app/bot.py."""
from __future__ import annotations

import pytest

from app.bot import UNAUTHORIZED_MESSAGE, WELCOME_MESSAGE, handle_update


def _make_update(text: str, chat_id: int = 42, user_id: int = 42) -> dict:
    return {"message": {"chat": {"id": chat_id}, "from": {"id": user_id}, "text": text}}


# ---------------------------------------------------------------------------
# /start command
# ---------------------------------------------------------------------------

async def test_start_command_sends_welcome(mocker):
    send = mocker.patch("app.bot.send_message", return_value=None)

    await handle_update(_make_update("/start"))

    send.assert_called_once_with(42, WELCOME_MESSAGE, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# Unknown commands are ignored
# ---------------------------------------------------------------------------

async def test_unknown_command_is_ignored(mocker):
    send = mocker.patch("app.bot.send_message", return_value=None)
    mocker.patch("app.bot.send_chat_action", return_value=None)

    await handle_update(_make_update("/unknown"))

    send.assert_not_called()


# ---------------------------------------------------------------------------
# Normal text triggers the full RAG flow
# ---------------------------------------------------------------------------

async def test_normal_text_triggers_rag_flow(mocker):
    mocker.patch("app.bot.send_chat_action", return_value=None)
    mocker.patch("app.bot.load_history", return_value=[])
    rag_mock = mocker.patch("app.bot.answer", return_value="The night is dark.")
    append_mock = mocker.patch("app.bot.append_message", return_value=None)
    send = mocker.patch("app.bot.send_message", return_value=None)

    await handle_update(_make_update("Who is Jon Snow?", chat_id=99))

    rag_mock.assert_called_once_with("Who is Jon Snow?", [])
    assert append_mock.call_count == 2
    append_mock.assert_any_call(99, "user", "Who is Jon Snow?")
    append_mock.assert_any_call(99, "assistant", "The night is dark.")
    send.assert_called_once_with(99, "The night is dark.")


# ---------------------------------------------------------------------------
# RAG exceptions surface as a user-facing error message
# ---------------------------------------------------------------------------

async def test_rag_exception_sends_error_message(mocker):
    mocker.patch("app.bot.send_chat_action", return_value=None)
    mocker.patch("app.bot.load_history", return_value=[])
    mocker.patch("app.bot.answer", side_effect=RuntimeError("Vertex AI down"))
    send = mocker.patch("app.bot.send_message", return_value=None)

    await handle_update(_make_update("Tell me about dragons", chat_id=7))

    send.assert_called_once()
    assert "ravens" in send.call_args.args[1]  # error message mentions ravens


# ---------------------------------------------------------------------------
# Update with no message field is a no-op
# ---------------------------------------------------------------------------

async def test_update_with_no_message_is_noop(mocker):
    send = mocker.patch("app.bot.send_message", return_value=None)

    await handle_update({"poll": {"id": "xyz"}})

    send.assert_not_called()


# ---------------------------------------------------------------------------
# Update with empty text is a no-op
# ---------------------------------------------------------------------------

async def test_update_with_empty_text_is_noop(mocker):
    send = mocker.patch("app.bot.send_message", return_value=None)

    await handle_update({"message": {"chat": {"id": 1}, "text": "   "}})

    send.assert_not_called()


# ---------------------------------------------------------------------------
# edited_message is handled the same as message
# ---------------------------------------------------------------------------

async def test_edited_message_is_handled(mocker):
    mocker.patch("app.bot.send_chat_action", return_value=None)
    mocker.patch("app.bot.load_history", return_value=[])
    mocker.patch("app.bot.answer", return_value="Fire and blood.")
    mocker.patch("app.bot.append_message", return_value=None)
    send = mocker.patch("app.bot.send_message", return_value=None)

    update = {"edited_message": {"chat": {"id": 5}, "text": "edited question"}}
    await handle_update(update)

    send.assert_called_once_with(5, "Fire and blood.")


# ---------------------------------------------------------------------------
# Authorization / allowlist
# ---------------------------------------------------------------------------

async def test_unauthorized_user_is_rejected(mocker):
    """A user not in the allowlist receives the unauthorized message."""
    import app.bot as bot_module
    mocker.patch.object(bot_module.settings, "allowed_user_ids", "111,222")
    send = mocker.patch("app.bot.send_message", return_value=None)

    await handle_update(_make_update("Hello", chat_id=99, user_id=999))

    send.assert_called_once_with(99, UNAUTHORIZED_MESSAGE)


async def test_authorized_user_is_allowed(mocker):
    """A user in the allowlist proceeds normally."""
    import app.bot as bot_module
    mocker.patch.object(bot_module.settings, "allowed_user_ids", "42")
    mocker.patch("app.bot.send_chat_action", return_value=None)
    mocker.patch("app.bot.load_history", return_value=[])
    mocker.patch("app.bot.answer", return_value="Winter is coming.")
    mocker.patch("app.bot.append_message", return_value=None)
    send = mocker.patch("app.bot.send_message", return_value=None)

    await handle_update(_make_update("Hello", chat_id=42, user_id=42))

    send.assert_called_once_with(42, "Winter is coming.")


async def test_empty_allowlist_allows_everyone(mocker):
    """An empty allowed_user_ids string means unrestricted access."""
    import app.bot as bot_module
    mocker.patch.object(bot_module.settings, "allowed_user_ids", "")
    mocker.patch("app.bot.send_chat_action", return_value=None)
    mocker.patch("app.bot.load_history", return_value=[])
    mocker.patch("app.bot.answer", return_value="All men must die.")
    mocker.patch("app.bot.append_message", return_value=None)
    send = mocker.patch("app.bot.send_message", return_value=None)

    await handle_update(_make_update("Hello", chat_id=1, user_id=99999))

    send.assert_called_once_with(1, "All men must die.")

