"""Tests for FastAPI endpoints in app/main.py."""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

async def test_health_check(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "iron-counsel"}


# ---------------------------------------------------------------------------
# POST /webhook — happy path
# ---------------------------------------------------------------------------

async def test_webhook_happy_path(client, mocker):
    mocker.patch("app.main.handle_update", return_value=None)

    update = {"message": {"chat": {"id": 1}, "text": "Hello"}}
    response = await client.post(
        "/webhook",
        json=update,
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}


# ---------------------------------------------------------------------------
# POST /webhook — secret token validation
# ---------------------------------------------------------------------------

async def test_webhook_wrong_secret_returns_403(client, mocker):
    mocker.patch("app.main.handle_update", return_value=None)

    response = await client.post(
        "/webhook",
        json={"message": {"chat": {"id": 1}, "text": "Hello"}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
    )
    assert response.status_code == 403


async def test_webhook_missing_secret_returns_403(client, mocker):
    mocker.patch("app.main.handle_update", return_value=None)

    # No secret token header at all
    response = await client.post(
        "/webhook",
        json={"message": {"chat": {"id": 1}, "text": "Hello"}},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# POST /webhook — non-message update is accepted but ignored
# ---------------------------------------------------------------------------

async def test_webhook_non_message_update(client, mocker):
    handle_mock = mocker.patch("app.main.handle_update", return_value=None)

    # Telegram can send poll, inline_query, etc. — should still return 200
    update = {"poll": {"id": "abc123"}}
    response = await client.post(
        "/webhook",
        json=update,
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
    )
    assert response.status_code == 200
    handle_mock.assert_called_once_with(update)
