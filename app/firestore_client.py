from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure

from app.config import settings

_db: firestore.AsyncClient | None = None


def get_db() -> firestore.AsyncClient:
    global _db
    if _db is None:
        _db = firestore.AsyncClient(project=settings.gcp_project_id)
    return _db


# ---------------------------------------------------------------------------
# Vector search on quotes collection
# ---------------------------------------------------------------------------

async def search_quotes(embedding: list[float], top_k: int | None = None) -> list[dict[str, Any]]:
    """Return top_k GoT quotes whose embeddings are nearest to the given vector."""
    k = top_k or settings.retriever_top_k
    db = get_db()
    collection = db.collection(settings.firestore_quotes_collection)

    vector_query = collection.find_nearest(
        vector_field="embedding",
        query_vector=Vector(embedding),
        distance_measure=DistanceMeasure.COSINE,
        limit=k,
    )

    results = []
    async for doc in vector_query.stream():
        data = doc.to_dict()
        results.append({
            "text": data.get("text", ""),
            "character": data.get("character", ""),
            "source": data.get("source", ""),
        })
    return results


async def add_quote(text: str, character: str, source: str, embedding: list[float]) -> str:
    """Write a single quote document to Firestore. Returns the new document ID."""
    db = get_db()
    doc_ref = db.collection(settings.firestore_quotes_collection).document()
    await doc_ref.set({
        "text": text,
        "character": character,
        "source": source,
        "embedding": Vector(embedding),
    })
    return doc_ref.id


# ---------------------------------------------------------------------------
# Conversation history (per chat_id)
# ---------------------------------------------------------------------------

def _messages_ref(chat_id: int | str) -> firestore.AsyncCollectionReference:
    db = get_db()
    return (
        db.collection(settings.firestore_conversations_collection)
        .document(str(chat_id))
        .collection("messages")
    )


async def load_history(chat_id: int | str) -> list[dict[str, str]]:
    """Return the last N messages for a chat as [{"role": ..., "content": ...}, ...]."""
    limit = settings.conversation_history_limit
    ref = _messages_ref(chat_id)
    query = ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)

    docs = []
    async for doc in query.stream():
        docs.append(doc.to_dict())

    # Reverse so oldest message comes first
    docs.reverse()
    return [{"role": d["role"], "content": d["content"]} for d in docs]


async def append_message(chat_id: int | str, role: str, content: str) -> None:
    """Append a single message to the conversation history."""
    ref = _messages_ref(chat_id)
    await ref.add({
        "role": role,
        "content": content,
        "timestamp": datetime.now(tz=timezone.utc),
    })
