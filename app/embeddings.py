"""Local embeddings via fastembed (ONNX runtime, no PyTorch required)."""
from __future__ import annotations

from langchain_community.embeddings import FastEmbedEmbeddings

# sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 → 384 dims
EMBEDDING_DIM = 384


def make_embeddings(model_name: str) -> FastEmbedEmbeddings:
    return FastEmbedEmbeddings(model_name=model_name)

