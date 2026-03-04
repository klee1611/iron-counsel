#!/usr/bin/env python3
"""
Ingest GoT quotes from a CSV into Firestore via a decoupled, two-phase pipeline:

  Phase 1 — embed:  CSV → vectors.json (local fastembed/ONNX, no API, no rate limits)
  Phase 2 — upload: vectors.json → Firestore (throttled parallel batch commits)
"""

import argparse
import asyncio
import csv
import json
import os
import sys
from tqdm import tqdm

from fastembed import TextEmbedding
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector

# ---------------------------------------------------------------------------
# 架構組態
# ---------------------------------------------------------------------------

GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "demo-project")
FIRESTORE_COLLECTION = os.environ.get("FIRESTORE_QUOTES_COLLECTION", "quotes")

FIRESTORE_BATCH_LIMIT = 500
CONCURRENCY_LIMIT_FIRESTORE = 10

EMULATOR_HOST = os.environ.get("FIRESTORE_EMULATOR_HOST")
if not EMULATOR_HOST:
    print("⚠️  Warning: FIRESTORE_EMULATOR_HOST is not set. Connecting to production?")

# ---------------------------------------------------------------------------
# 欄位解析邏輯
# ---------------------------------------------------------------------------

TEXT_CANDIDATES = ["sentence", "text", "line", "quote", "dialog", "dialogue"]
CHARACTER_CANDIDATES = ["name", "character", "speaker", "character_name"]
SOURCE_CANDIDATES = ["season", "episode", "source", "chapter"]

def _find_col(headers: list[str], candidates: list[str]) -> str | None:
    lower = [h.lower().strip() for h in headers]
    for c in candidates:
        if c in lower:
            return headers[lower.index(c)]
    return None

def load_csv(csv_path: str) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames or [])
        text_col = _find_col(headers, TEXT_CANDIDATES)
        char_col = _find_col(headers, CHARACTER_CANDIDATES)
        src_col = _find_col(headers, SOURCE_CANDIDATES)
        if not text_col:
            raise ValueError(f"Could not find a text column in: {headers}")
        print(f"✅ Columns identified → text='{text_col}', character='{char_col}', source='{src_col}'")
        rows = []
        for row in reader:
            text = row.get(text_col, "").strip()
            if text:
                rows.append({
                    "text": text,
                    "character": row.get(char_col, "Unknown").strip() if char_col else "Unknown",
                    "source": row.get(src_col, "").strip() if src_col else "",
                })
    return rows

# ---------------------------------------------------------------------------
# Phase 1: Embed (CSV → vectors.json)
# ---------------------------------------------------------------------------

def embed_phase(rows: list[dict], vectors_file: str, batch_size: int = 500) -> list[dict]:
    """Embed locally with fastembed (ONNX). No API calls, no rate limits."""
    model_name = os.environ.get("EMBEDDING_MODEL_NAME", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    print(f"🤖 Loading embedding model: {model_name}")
    embedder = TextEmbedding(model_name=model_name)

    # Checkpoint resumption
    checkpoint: list[dict] = []
    if os.path.exists(vectors_file):
        try:
            with open(vectors_file, encoding="utf-8") as f:
                checkpoint = json.load(f)
            print(f"📂 Resuming from checkpoint: {len(checkpoint)} rows already embedded.")
        except (json.JSONDecodeError, OSError):
            checkpoint = []

    already_done = len(checkpoint)
    remaining = rows[already_done:]
    if not remaining:
        print("✅ All rows already embedded in checkpoint.")
        return checkpoint

    batches = [remaining[i : i + batch_size] for i in range(0, len(remaining), batch_size)]
    print(f"🚀 Phase 1: Embedding {len(remaining)} remaining quotes in {len(batches)} batches (batch_size={batch_size})")

    records = list(checkpoint)
    pbar = tqdm(total=len(batches), desc="Embedding", unit="batch")

    for batch_rows in batches:
        texts = [r["text"] for r in batch_rows]
        # fastembed returns a generator of numpy arrays
        embeddings_list = [emb.tolist() for emb in embedder.embed(texts, batch_size=batch_size)]
        records.extend(
            {**row, "embedding": emb}
            for row, emb in zip(batch_rows, embeddings_list)
        )
        with open(vectors_file, "w", encoding="utf-8") as f:
            json.dump(records, f)
        pbar.update(1)

    pbar.close()
    print(f"✅ Embed complete — {len(records)} vectors saved to {vectors_file}.")
    return records

# ---------------------------------------------------------------------------
# Phase 2: Upload (vectors.json → Firestore)
# ---------------------------------------------------------------------------

async def upload_phase(records: list[dict]) -> None:
    db = firestore.AsyncClient(project=GCP_PROJECT_ID)
    collection = db.collection(FIRESTORE_COLLECTION)
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT_FIRESTORE)
    batches = [records[i : i + FIRESTORE_BATCH_LIMIT] for i in range(0, len(records), FIRESTORE_BATCH_LIMIT)]

    print(f"🚀 Phase 2: Uploading {len(records)} docs in {len(batches)} batches...")
    pbar = tqdm(total=len(batches), desc="Firestore Upload")

    async def commit_batch(idx: int, batch_records: list[dict]) -> None:
        async with sem:
            try:
                fs_batch = db.batch()
                for rec in batch_records:
                    doc_ref = collection.document()
                    fs_batch.set(doc_ref, {
                        "text": rec["text"],
                        "character": rec["character"],
                        "source": rec["source"],
                        "embedding": Vector(rec["embedding"]),
                    })
                await fs_batch.commit()
                pbar.update(1)
            except Exception as e:
                print(f"\n❌ Upload Error in batch {idx + 1}: {e}")

    await asyncio.gather(*[commit_batch(i, b) for i, b in enumerate(batches)])
    pbar.close()
    print(f"✅ {len(records)} quotes ingested into '{FIRESTORE_COLLECTION}'.")

# ---------------------------------------------------------------------------
# 主執行邏輯
# ---------------------------------------------------------------------------

async def run(args: argparse.Namespace) -> None:
    if args.upload_only:
        if not os.path.exists(args.vectors_file):
            sys.exit(f"Error: vectors file not found: {args.vectors_file}")
        with open(args.vectors_file, encoding="utf-8") as f:
            records = json.load(f)
        await upload_phase(records)
        return

    if not os.path.exists(args.csv):
        sys.exit(f"Error: CSV file not found: {args.csv}")

    rows = load_csv(args.csv)

    if not args.embed_only and os.path.exists(args.vectors_file) and not args.force:
        print(f"📂 Found existing {args.vectors_file}. Skipping embed phase.")
        with open(args.vectors_file, encoding="utf-8") as f:
            records = json.load(f)
    else:
        records = embed_phase(rows, args.vectors_file, args.batch_size)

    if not args.embed_only and records:
        await upload_phase(records)

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest GoT quotes into Firestore")
    parser.add_argument("--csv", default="Game_of_Thrones_Script.csv")
    parser.add_argument("--vectors-file", default="vectors.json")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--embed-only", action="store_true")
    parser.add_argument("--upload-only", action="store_true")
    args = parser.parse_args()

    if args.embed_only and args.upload_only:
        sys.exit("Error: --embed-only and --upload-only are mutually exclusive.")

    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\n🛑 Interrupted.")

if __name__ == "__main__":
    main()
