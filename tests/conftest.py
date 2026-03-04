"""Shared pytest fixtures for Iron Counsel tests."""
from __future__ import annotations

import os

# Set env vars at module level so they're in place before any app module is imported.
os.environ.setdefault("TELEGRAM_TOKEN", "test-token-123")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "test-secret")
os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("ALLOWED_USER_IDS", "")  # allow all users in tests

import pytest
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Async FastAPI test client
# ---------------------------------------------------------------------------

@pytest.fixture
async def client():
    """httpx AsyncClient wired to the FastAPI app (no real network calls)."""
    from app.main import app as fastapi_app
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url="http://test"
    ) as ac:
        yield ac
