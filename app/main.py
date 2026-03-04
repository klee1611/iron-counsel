from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel

from app.bot import handle_update
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate critical config at startup
    if not settings.telegram_token:
        raise RuntimeError("TELEGRAM_TOKEN is not set")
    if not settings.gcp_project_id:
        raise RuntimeError("GCP_PROJECT_ID is not set")
    logger.info("Iron Counsel starting up. Project=%s", settings.gcp_project_id)
    yield
    logger.info("Iron Counsel shutting down.")


app = FastAPI(title="Iron Counsel", lifespan=lifespan)


@app.get("/")
async def health_check():
    return {"status": "ok", "service": "iron-counsel"}


@app.post("/webhook")
async def webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    # Verify Telegram webhook secret if configured
    if settings.telegram_webhook_secret:
        if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid secret token")

    update = await request.json()
    logger.debug("Received update: %s", update)

    await handle_update(update)

    # Always return 200 so Telegram doesn't retry
    return {"ok": True}


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
async def chat(req: ChatRequest):
    """Local development only — bypasses Telegram, calls RAG pipeline directly.
    Only active when DEBUG=true (set in docker-compose.override.yml, never in production).
    """
    if os.environ.get("DEBUG", "").lower() != "true":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    from app.rag import answer
    reply = await answer(req.message, [])
    return {"reply": reply}
