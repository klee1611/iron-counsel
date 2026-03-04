"""Tests for the RAG chain in app/rag.py."""
from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.rag import SYSTEM_PROMPT, _format_quotes, answer


# ---------------------------------------------------------------------------
# _format_quotes
# ---------------------------------------------------------------------------

def test_format_quotes_empty():
    assert _format_quotes([]) == "(No relevant quotes found.)"


def test_format_quotes_single_with_source():
    quotes = [{"text": "Winter is coming.", "character": "Eddard Stark", "source": "Season 1"}]
    result = _format_quotes(quotes)
    assert '"Winter is coming."' in result
    assert "Eddard Stark" in result
    assert "[Season 1]" in result


def test_format_quotes_single_without_source():
    quotes = [{"text": "A Lannister always pays his debts.", "character": "Tyrion", "source": ""}]
    result = _format_quotes(quotes)
    assert "Tyrion" in result
    assert "[]" not in result  # empty source should not render brackets


def test_format_quotes_multiple():
    quotes = [
        {"text": "Quote one.", "character": "Arya Stark", "source": "S3"},
        {"text": "Quote two.", "character": "Cersei", "source": "S2"},
    ]
    result = _format_quotes(quotes)
    assert "Arya Stark" in result
    assert "Cersei" in result
    assert result.count("\n") == 1  # two lines → one newline between them


# ---------------------------------------------------------------------------
# answer() — verifies correct LangChain message construction
# ---------------------------------------------------------------------------

async def test_answer_calls_llm_with_correct_message_order(mocker):
    # Mock embeddings
    mocker.patch(
        "app.rag.get_embeddings",
        return_value=mocker.Mock(embed_query=mocker.Mock(return_value=[0.1] * 768)),
    )
    # Mock Firestore quote retrieval
    mocker.patch(
        "app.rag.search_quotes",
        return_value=[{"text": "Fire and blood.", "character": "Daenerys", "source": "S7"}],
    )
    # Mock the LLM
    fake_llm = mocker.AsyncMock()
    fake_llm.ainvoke = mocker.AsyncMock(return_value=mocker.Mock(content="Here is my answer."))
    mocker.patch("app.rag.get_llm", return_value=fake_llm)

    history = [
        {"role": "user", "content": "Who rules Westeros?"},
        {"role": "assistant", "content": "Many claim the throne."},
    ]
    result = await answer("Tell me about dragons.", history)

    assert result == "Here is my answer."

    # Inspect the messages passed to ainvoke
    call_args = fake_llm.ainvoke.call_args[0][0]
    assert isinstance(call_args[0], SystemMessage)
    assert "Fire and blood." in call_args[0].content  # quote injected into system prompt
    assert isinstance(call_args[1], HumanMessage)
    assert call_args[1].content == "Who rules Westeros?"
    assert isinstance(call_args[2], AIMessage)
    assert call_args[2].content == "Many claim the throne."
    assert isinstance(call_args[3], HumanMessage)
    assert call_args[3].content == "Tell me about dragons."


async def test_answer_with_no_history(mocker):
    mocker.patch(
        "app.rag.get_embeddings",
        return_value=mocker.Mock(embed_query=mocker.Mock(return_value=[0.0] * 768)),
    )
    mocker.patch("app.rag.search_quotes", return_value=[])
    fake_llm = mocker.AsyncMock()
    fake_llm.ainvoke = mocker.AsyncMock(return_value=mocker.Mock(content="No quotes, still answers."))
    mocker.patch("app.rag.get_llm", return_value=fake_llm)

    result = await answer("What is the Red Wedding?", [])

    assert result == "No quotes, still answers."
    messages = fake_llm.ainvoke.call_args[0][0]
    # System + user query only (no history messages)
    assert len(messages) == 2
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)


async def test_answer_system_prompt_contains_bilingual_instruction(mocker):
    """Verify the system prompt enforces the bilingual English + Mandarin rule."""
    mocker.patch(
        "app.rag.get_embeddings",
        return_value=mocker.Mock(embed_query=mocker.Mock(return_value=[0.0] * 768)),
    )
    mocker.patch("app.rag.search_quotes", return_value=[])
    fake_llm = mocker.AsyncMock()
    fake_llm.ainvoke = mocker.AsyncMock(return_value=mocker.Mock(content="ok"))
    mocker.patch("app.rag.get_llm", return_value=fake_llm)

    await answer("Hello", [])

    system_content = fake_llm.ainvoke.call_args[0][0][0].content
    assert "Traditional Chinese" in system_content
    assert "English" in system_content
