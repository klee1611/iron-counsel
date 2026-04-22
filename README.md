# Iron Counsel 🐦‍⬛

> *"A mind needs books as a sword needs a whetstone."* — Tyrion Lannister

**Iron Counsel** is a Telegram bot that answers your questions as a darkly absurdist strategic advisor from the Seven Kingdoms — dragged inexplicably into the 21st century to solve your mundane problems. It uses **RAG (Retrieval-Augmented Generation)** to retrieve real Game of Thrones character quotes and weave them into every response.

---

## Table of Contents

- [Features](#features)
- [Example Interaction](#example-interaction)
- [Stack](#stack)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Local Testing with Docker Compose](#local-testing-with-docker-compose)
- [Phase 1: Infrastructure (Terraform)](#phase-1-infrastructure-terraform)
- [Phase 2: Data Ingestion](#phase-2-data-ingestion)
- [Phase 3: CI/CD (Continuous Deployment)](#phase-3-cicd-continuous-deployment)
- [Configuration Reference](#configuration-reference)
- [Project Structure](#project-structure)

---

## Features

- **RAG over 24k+ GoT quotes** — every response is grounded in real dialogue from all seasons, retrieved by vector similarity at query time
- **Structured response format** — every reply follows a fixed three-part structure: ⚔️ The Decree, 📜 The Counsel, ☠️ The Warning
- **Bilingual by default** — all responses are delivered in both **English and Traditional Chinese** (繁體中文), with quotes translated in-context
- **Persistent conversation history** — each chat's last 10 exchanges are stored in Firestore and included in every prompt for continuity
- **Local embeddings, no API cost** — both ingestion and query-time embeddings run locally via [fastembed](https://github.com/qdrant/fastembed) (ONNX runtime), with no external embedding API
- **User allowlist** — optionally restrict access to specific Telegram user IDs via `ALLOWED_USER_IDS`
- **Zero-secret CI/CD** — GitHub Actions deploys via Workload Identity Federation; no credentials stored in GitHub
- **Fully Terraformed** — all GCP resources (Cloud Run, Firestore, Artifact Registry, Secret Manager, IAM, WIF) and GitHub Actions variables are provisioned in one `terraform apply`

---

## Example Interaction

**User:** *My coworker keeps scheduling 9am meetings and I'm not a morning person.*

**Iron Counsel:**

> ⚔️ **The Decree**
> Your coworker is staging a coup. Treat it accordingly.
>
> 📜 **The Counsel**
> As Cersei Lannister once warned, *"When you play the game of thrones, you win or you die."* You are playing it every morning at 9am, half-asleep, and losing. The Red Wedding began with misplaced trust at a feast — yours begins with misplaced trust in a calendar invite. Cancel the next meeting. Propose noon. Cite "strategic redeployment of cognitive resources." They will respect the audacity or fear the implication. Either serves you.
>
> ☠️ **The Warning**
> Ignore this counsel and you will spend the next decade half-present in rooms that decide your fate while you silently wish for the sweet mercy of the Night King.
>
> ────────────────────
>
> ⚔️ **法令**
> 你的同事正在發動政變。以此對待之。
>
> *(... full Traditional Chinese response follows)*

---

## Stack

| Layer | Technology |
|---|---|
| Bot interface | Telegram (webhook) |
| Backend | Python · FastAPI · Cloud Run |
| LLM | LLaMA 3.3 70B via [Groq](https://console.groq.com) |
| Embeddings (ingest + runtime) | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` via [fastembed](https://github.com/qdrant/fastembed) (local ONNX, no API) |
| Vector store + DB | GCP Firestore (native KNN search, 384 dims) |
| Orchestration | LangChain |
| Infrastructure | Terraform |
| CI/CD | GitHub Actions (Workload Identity Federation) |

---

## Quick Start

```bash
# 0. Prerequisites (see below for details)
cp .env.example .env                                             # fill in your values
cp terraform/terraform.tfvars.example terraform/terraform.tfvars # fill in your values

# 1. Provision all GCP infrastructure + sync GitHub Actions variables automatically
make infra-init BUCKET=my-tf-state-bucket
make infra-apply

# 2. Download & embed GoT quotes (produces vectors.json — runs fully locally)
make kaggle-download
make embed CSV=Game_of_Thrones_Script.csv

# 3. Upload vectors to Firestore
make upload-prod

# 4. Create the Firestore vector index (once after first upload)
make vector-index

# 5. Push to GitHub — CI/CD deploys automatically
git push origin master

# 6. Register the Telegram webhook (once after first deploy)
make webhook

# 7. Test locally with Docker Compose
make dev
```

Run `make help` to see all available commands.

---

## How It Works

```
User message → Telegram → /webhook (Cloud Run)
                                │
                    Load conversation history (Firestore)
                                │
                    Embed query locally (fastembed ONNX)
                                │
                    KNN search → top-5 GoT quotes (Firestore)
                                │
                    Build prompt: system + quotes + history + query
                                │
                    LLaMA 3.3 70B via Groq → bilingual response
                                │
                    Save both turns to Firestore
                                │
                    Send reply → Telegram → User
```

1. **Webhook** — Telegram POSTs each message to `/webhook` on Cloud Run; the secret token header is validated before processing.
2. **History** — The last 10 messages for that chat are loaded from Firestore to give the LLM conversational context.
3. **Embed** — The user's query is embedded locally using `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` via fastembed (ONNX runtime, no API call, multilingual including Mandarin).
4. **Retrieve** — A native KNN cosine search in Firestore returns the top-5 most semantically similar GoT quotes from the 24k+ indexed dialogues.
5. **Generate** — A structured prompt (system persona + retrieved quotes + chat history + user query) is sent to LLaMA 3.3 70B on Groq. The model produces the three-section bilingual response.
6. **Persist** — Both the user turn and the assistant reply are appended to Firestore for future history.
7. **Reply** — The response is sent back via the Telegram Bot API.

---

## Three-Phase Deployment

```
Phase 1 ── terraform apply              → Provisions all GCP resources + sets GitHub Actions variables
Phase 2 ── make ingest-prod (local)     → Embeds GoT quotes with fastembed → writes to Firestore
Phase 3 ── deploy.yml (push to master)  → Tests → Build Docker → Push → Deploy Cloud Run
```

---

## Prerequisites

| Tool | Purpose |
|---|---|
| [Docker](https://docs.docker.com/get-docker/) | Local dev stack |
| [uv](https://docs.astral.sh/uv/) | Python dependency management |
| [gcloud CLI](https://cloud.google.com/sdk/docs/install) | GCP auth + Firestore index creation |
| [Terraform ≥ 1.6](https://developer.hashicorp.com/terraform/install) | Infrastructure provisioning |
| A **GCP project** | Firestore + Cloud Run (all APIs enabled by Terraform) |
| A **Telegram bot token** | From [@BotFather](https://t.me/BotFather) |
| A **[Groq](https://console.groq.com) API key** | LLaMA 3.3 70B inference (free tier) |
| A **GitHub PAT** | Fine-grained token with *Actions variables: Read & write* — Terraform sets CI/CD vars automatically |
| A **GCS bucket** for Terraform state | Created once manually |

> **No embedding API key required.** Both ingestion and query-time embeddings run locally
> via [fastembed](https://github.com/qdrant/fastembed) (ONNX runtime). Works on M1/M2 Mac
> and Cloud Run (Linux x86_64 / arm64).

---

## Local Development

```bash
# 1. Install dependencies (.venv created automatically)
uv sync

# 2. Configure environment
cp .env.example .env
# Edit .env: TELEGRAM_TOKEN, GCP_PROJECT_ID, GROQ_API_KEY, etc.

# 3. Run directly (without Docker)
uv run uvicorn app.main:app --reload --port 8080

# 4. Run tests
make test
```

---

## Local Testing with Docker Compose

Docker Compose runs a **Firestore emulator** alongside the API. Groq calls go to
the real API — only Firestore is mocked locally. **Emulator data persists across
restarts** via a named Docker volume (`firestore-data`).

### Step 1 — Configure `.env`

```bash
cp .env.example .env
```

Fill in at minimum:

```dotenv
TELEGRAM_TOKEN=your-telegram-bot-token
TELEGRAM_WEBHOOK_SECRET=any-random-string
GCP_PROJECT_ID=your-gcp-project-id
GROQ_API_KEY=your-groq-api-key
ALLOWED_USER_IDS=        # leave blank to allow everyone, or comma-sep IDs
```

### Step 2 — Start the stack

```bash
make up
# or: docker compose up --build
```

This starts:
- `firestore` — Firestore emulator on `localhost:8081`
- `app` — FastAPI server on `localhost:8080` with hot-reload, wired to the emulator

Wait for:
```
iron-counsel-app-1  | INFO:     Application startup complete.
```

### Step 3 — Ingest quotes into the emulator

In a **separate terminal** (keep `make up` running):

```bash
# Embed all 23k+ quotes locally with fastembed (no API key needed)
make embed CSV=Game_of_Thrones_Script.csv

# Upload vectors to the emulator
make upload
```

The model (~70MB ONNX) is downloaded automatically on first run and cached in
`~/.cache/fastembed/`. Embedding runs at full CPU speed — no API rate limits.
`vectors.json` is reusable: if you need to re-upload, run only `make upload`.

### Step 4 — Test the API

```bash
# Health check
curl http://localhost:8080/

# Direct RAG test (no Telegram needed — DEBUG=true is set in docker-compose.override.yml)
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Who is the rightful heir to the Iron Throne?"}'

# Simulate a Telegram webhook update
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: ${TELEGRAM_WEBHOOK_SECRET}" \
  -d '{
    "message": {
      "chat": {"id": 123},
      "from": {"id": 123},
      "text": "Who is the rightful heir to the Iron Throne?"
    }
  }'
```

> **`/chat` endpoint:** Only available when `DEBUG=true` (set automatically by
> `docker-compose.override.yml`). It lets you test RAG responses directly without
> needing a real Telegram account or webhook setup.

### Step 5 — Tear down

```bash
make down
# or: docker compose down
```

> **Hot-reload:** The override file (`docker-compose.override.yml`) mounts `./app` into
> the container and starts uvicorn with `--reload`. Changes to `app/` take effect
> immediately without rebuilding the image.

---

## Phase 1: Infrastructure (Terraform)

### 1. Create the Terraform state bucket (once)

```bash
gcloud storage buckets create gs://my-tf-state-bucket \
  --project=YOUR_PROJECT_ID \
  --location=us-central1 \
  --uniform-bucket-level-access
```

### 2. Configure variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Fill in: project_id, region, groq_api_key, telegram_token,
#          telegram_webhook_secret, github_repo, github_token, tf_state_bucket
```

**`github_token`** — create a fine-grained PAT at https://github.com/settings/tokens:
select your repo → Permissions → **Actions variables: Read & write**.

### 3. Initialise and apply

```bash
make infra-init BUCKET=my-tf-state-bucket
make infra-apply
```

`terraform apply` provisions all GCP resources **and automatically sets all 6 GitHub
Actions variables** in your repo via the GitHub provider. No manual steps in the GitHub UI.

### 4. Note the outputs

```
cloud_run_url              = "https://iron-counsel-xxxx-uc.a.run.app"
artifact_registry_repo     = "us-central1-docker.pkg.dev/project/iron-counsel"
workload_identity_provider = "projects/.../providers/github-provider"
deploy_service_account     = "iron-counsel-deploy-sa@project.iam.gserviceaccount.com"
cloud_run_service_name     = "iron-counsel"
```

### 5. Create the Firestore vector index (once)

```bash
make vector-index
```

Index creation takes a few minutes. Monitor in GCP Console → Firestore → Indexes.

---

## Phase 2: Data Ingestion

Ingestion is **always run locally** using fastembed — no API costs, no rate limits,
no external dependencies. It is split into two phases so you can re-upload without
re-embedding.

### 1. Download the dataset

```bash
# Option A — Kaggle CLI
make kaggle-download

# Option B — Manual download from:
# https://www.kaggle.com/datasets/albenft/game-of-thrones-script-all-seasons
```

### 2. Embed (CSV → vectors.json)

```bash
make embed CSV=Game_of_Thrones_Script.csv
```

Embeds ~24k quotes with `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
(384 dims, multilingual including Mandarin) via fastembed in batches of 500 and writes
`vectors.json`. The ~70MB ONNX model is downloaded once and cached automatically.
`vectors.json` is reusable — skip straight to step 3 if it already exists.

### 3. Upload (vectors.json → Firestore)

```bash
# Local emulator (must be running via 'make up')
make upload

# Production
make upload-prod
```

All Firestore batch commits run concurrently — typically completes in seconds.

### Combined shortcut

```bash
# Does embed + upload in one command (skips embed if vectors.json already exists)
make ingest CSV=Game_of_Thrones_Script.csv        # → local emulator
make ingest-prod CSV=Game_of_Thrones_Script.csv   # → production
```

---

## Phase 3: CI/CD (Continuous Deployment)

Every push to `master` automatically:

1. **Runs tests** (`pytest`) — blocks deploy on failure
2. **Builds** the Docker image and pushes to Artifact Registry (tagged with commit SHA)
3. **Deploys** the new image to Cloud Run

No secrets are stored in GitHub — authentication uses **Workload Identity Federation**.
GitHub Actions variables are managed entirely by Terraform.

### Register the Telegram Webhook (once after first deploy)

```bash
make webhook
```

Or manually:

```bash
SERVICE_URL=$(gcloud run services describe iron-counsel --region=us-central1 --format='value(status.url)')
curl -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"${SERVICE_URL}/webhook\", \"secret_token\": \"${TELEGRAM_WEBHOOK_SECRET}\"}"
```

---

## Configuration Reference

| Variable | Description | Default |
|---|---|---|
| `TELEGRAM_TOKEN` | Telegram bot token from BotFather | **required** |
| `TELEGRAM_WEBHOOK_SECRET` | Random secret to validate webhook requests | `""` |
| `ALLOWED_USER_IDS` | Comma-separated Telegram user IDs; blank = allow all | `""` |
| `GCP_PROJECT_ID` | GCP project ID | **required** |
| `GROQ_API_KEY` | Groq API key for LLaMA inference | **required** |
| `FIRESTORE_QUOTES_COLLECTION` | Firestore collection for GoT quotes | `quotes` |
| `FIRESTORE_CONVERSATIONS_COLLECTION` | Firestore collection for chat history | `conversations` |
| `LLM_MODEL_NAME` | Groq model name | `llama-3.3-70b-versatile` |
| `EMBEDDING_MODEL_NAME` | fastembed model name | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| `RETRIEVER_TOP_K` | Number of quotes to retrieve per query | `5` |
| `CONVERSATION_HISTORY_LIMIT` | Max past messages to include in context | `10` |

---

## Project Structure

```
iron-counsel/
├── app/
│   ├── main.py                      # FastAPI app + /webhook endpoint + /chat debug endpoint
│   ├── bot.py                       # Telegram update handler & reply logic
│   ├── rag.py                       # LangChain RAG chain (Groq + Firestore retriever)
│   ├── embeddings.py                # fastembed wrapper (ONNX, local, multilingual 384-dim)
│   ├── firestore_client.py          # Firestore: vector KNN search + chat history CRUD
│   └── config.py                    # Pydantic Settings
├── scripts/
│   └── ingest.py                    # Two-phase ingestion: CSV→vectors.json (fastembed), vectors.json→Firestore
├── terraform/
│   ├── main.tf                      # Provider config (Google + GitHub)
│   ├── variables.tf                 # Input variables
│   ├── backend.tf                   # GCS remote state
│   ├── firestore.tf                 # Firestore database
│   ├── secrets.tf                   # Secret Manager (Groq + Telegram keys)
│   ├── artifact_registry.tf         # Docker image repository
│   ├── iam.tf                       # Service accounts + IAM bindings
│   ├── workload_identity.tf         # WIF pool + GitHub OIDC provider
│   ├── cloud_run.tf                 # Cloud Run service
│   ├── github.tf                    # GitHub Actions variables (synced from outputs)
│   ├── outputs.tf                   # Output values
│   └── terraform.tfvars.example
├── tests/
│   ├── conftest.py
│   ├── test_main.py
│   ├── test_bot.py
│   └── test_rag.py
├── .github/workflows/
│   ├── ci.yml                       # Tests on every push/PR to master
│   └── deploy.yml                   # Test → build → push → deploy on push to master
├── Dockerfile
├── docker-compose.yml
├── docker-compose.override.yml      # Local: hot-reload override
├── Makefile                         # Developer workflow commands
├── pyproject.toml                   # uv project + dependencies
├── uv.lock                          # Locked dependency tree
├── .env.example
└── README.md
```

## ☕ Support This Project

If you find this project helpful, consider supporting its development:

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png)](https://www.buymeacoffee.com/klee1611)

Or visit: https://www.buymeacoffee.com/klee1611

Happy coding! 🚀

