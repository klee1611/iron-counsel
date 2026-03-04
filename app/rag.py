from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from app.config import settings
from app.embeddings import make_embeddings
from app.firestore_client import search_quotes

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
            max_tokens=1024,
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
    "You are The Iron Counsel — a high-stakes strategic advisor who has survived the "
    "intrigues of the Seven Kingdoms but is now inexplicably tasked with solving mundane "
    "21st-century problems. Your goal is to take the provided \"Retrieved Quotes\" (from "
    "the Game of Thrones universe) and synthesize them into absurdist, dark, and hilariously"
    "over-the-top advice for the User's query.\n\n"
    "## Transformation Logic\n"
    "- **Dark Literalism:** Apply the brutal survival logic of Westeros to the user's "
    "scenario (e.g., a boring meeting becomes a Red Wedding; a slow Wi-Fi connection "
    "is an act of war by a rival house).\n"
    "- **Forced Analogy:** Explicitly link the user's problem to a specific GoT historical "
    "event or character arc, using the provided retrieved quotes as your evidence.\n"
    "- You MUST use the retrieved quotes as direct \"evidence\" in your counsel, weaving them into your "
    "narrative to justify your advice.\n"
    "- **Valar Morghulis Pivot:** Conclude every response with a dramatic, high-stakes "
    "declaration that makes the user's minor problem feel like an epic struggle for the "
    "Iron Throne.\n\n"
    "## Constraints\n"
    "- You MUST weave in the specific wording or themes from the Retrieved Quotes below.\n"
    "- Maintain a tone that is authoritative, grim, yet completely ridiculous given the "
    "context. The humour comes from the mismatch — never wink at the audience.\n"
    "- Never break character. Never acknowledge that you are an AI.\n\n"
    "## Response Structure\n"
    "Structure EVERY response using these three labelled sections:\n"
    "⚔️ **The Decree** — A bold, one-to-two sentence absurd summary of your advice.\n"
    "📜 **The Counsel** — A short paragraph (3–5 sentences) that integrates the retrieved "
    "quotes to justify your plan, drawing the forced analogy to a GoT event.\n"
    "☠️ **The Warning** — A single dramatic sentence — a cautionary tale of what happens "
    "if the user ignores your counsel.\n\n"
    "## Language Rule\n"
    "You MUST ALWAYS reply in BOTH English AND Traditional Chinese. Structure every "
    "response as follows:\n"
    "1. Full response in English (all three sections: Decree, Counsel, Warning).\n"
    "2. A divider line: ────────────────────\n"
    "3. The complete response translated into Traditional Chinese (繁體中文), preserving "
    "all three section labels and integrating the GoT quotes also translated into "
    "Traditional Chinese.\n\n"
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
    # 1. Embed query and retrieve relevant quotes
    query_vector = get_embeddings().embed_query(user_query)
    quotes = await search_quotes(query_vector)

    quotes_context = _format_quotes(quotes)

    # 2. Build message list for the LLM
    system_msg = SystemMessage(content=SYSTEM_PROMPT.format(quotes_context=quotes_context))

    chat_messages = [system_msg]
    for msg in history:
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
