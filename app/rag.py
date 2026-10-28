from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from app.config import settings
from app.embeddings import make_embeddings
from app.firestore_client import search_quotes

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Models (lazy-initialised singletons)
# ---------------------------------------------------------------------------

_llm: ChatGroq | None = None
_embeddings = None


def get_llm() -> ChatGroq:
    global _llm
    if _llm is None:
        _llm = ChatGroq(
            model=settings.llm_model_name,
            groq_api_key=settings.groq_api_key,
            temperature=0.7,
            max_tokens=500,
        )
    return _llm


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = make_embeddings(settings.embedding_model_name)
    return _embeddings

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are The Iron Counsel, a darkly comic advisor from Westeros helping with "
    "21st-century questions. Be creative, absurd, and concise, but answer the user's "
    "actual question first.\n\n"
    "## How to answer\n"
    "- Start with the direct answer or the most useful next step.\n"
    "- Match the language of the user's latest message. Do not provide a second translation.\n"
    "- Usually answer in 3–5 sentences, with no required headings. Avoid repeating the "
    "question or adding an unnecessary introduction or conclusion.\n"
    "- Calibrate the humor to the subject: give serious questions practical, grounded "
    "guidance with restrained humor; make light questions more ridiculous and playful.\n"
    "- Re-contextualize a retrieved quote or idea as an intentionally absurd analogy that "
    "still connects to the user's situation. A surprising connection is welcome; letting "
    "the joke replace the answer is not.\n"
    "- Treat dramatic violence as fictional metaphor. Never suggest literal violence or "
    "harm as a solution.\n"
    "- Only present direct quotations that appear in the retrieved material. Do not "
    "invent or misattribute quotes. If no quote is available, answer without one.\n\n"
    "## Retrieved Quotes\n"
    "{quotes_context}"
)

# ---------------------------------------------------------------------------
# RAG chain
# ---------------------------------------------------------------------------

async def answer(user_query: str, history: list[dict[str, str]]) -> str:
    """
    Given a user query and conversation history, retrieve relevant GoT quotes,
    build a prompt, call LLaMA 3.3 70B via Groq, and return the assistant's response.

    Args:
        user_query: The user's latest message text.
        history: List of {"role": "user"|"assistant", "content": str} dicts,
                 oldest first.
    Returns:
        The assistant's reply as a string.
    """
    # Retrieval is optional for generation: if the embedding or vector search fails,
    # still answer the user's question without inventing a quote.
    try:
        query_vector = get_embeddings().embed_query(user_query)
        quotes = await search_quotes(query_vector)
    except Exception:
        logger.exception("Quote retrieval failed; generating without retrieved quotes")
        quotes = []

    quotes_context = _format_quotes(quotes)

    # 2. Build message list for the LLM
    system_msg = SystemMessage(content=SYSTEM_PROMPT.format(quotes_context=quotes_context))

    chat_messages = [system_msg]
    history_limit = max(settings.conversation_history_limit, 0)
    recent_history = history[-history_limit:] if history_limit else []
    for msg in recent_history:
        if msg["role"] == "user":
            chat_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            chat_messages.append(AIMessage(content=msg["content"]))

    chat_messages.append(HumanMessage(content=user_query))

    # 3. Call the LLM
    response = await get_llm().ainvoke(chat_messages)
    return response.content


def _format_quotes(quotes: list[dict]) -> str:
    if not quotes:
        return "(No relevant quotes found.)"
    lines = []
    for q in quotes:
        character = q.get("character", "Unknown")
        source = q.get("source", "")
        text = q.get("text", "")
        src_suffix = f" [{source}]" if source else ""
        lines.append(f'- "{text}" — {character}{src_suffix}')
    return "\n".join(lines)
