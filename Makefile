# Iron Counsel — Developer Makefile
# Run `make help` to see all available targets.

.PHONY: help \
        infra-init infra-plan infra-apply infra-destroy infra-output \
        setup up down logs test \
        kaggle-download embed upload upload-prod ingest ingest-prod vector-index \
        webhook \
        bootstrap dev

# ── Defaults ────────────────────────────────────────────────────────────────

# Kaggle dataset slug (override with: make kaggle-download DATASET=owner/slug)
DATASET    ?= albenft/game-of-thrones-script-all-seasons
# CSV path for ingestion (override with: make ingest CSV=path/to/file.csv)
CSV          ?= Game_of_Thrones_Script.csv
# Intermediate vectors JSON file (can be reused to skip re-embedding)
VECTORS_FILE ?= vectors.json
# Texts per Google AI embed call (100 → 240 batches for GoT, fits 100 req/min quota)
BATCH_SIZE   ?= 500
# Embedding model for fastembed (ONNX, no API key needed)
EMBEDDING_MODEL_NAME ?= sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
# Your GCP project (falls back to what's in .env if set)
PROJECT_ID ?= $(shell grep -E '^GCP_PROJECT_ID=' .env 2>/dev/null | cut -d= -f2)
# GCP region (falls back to .env, then us-central1)
REGION     ?= $(shell grep -E '^GCP_REGION=' .env 2>/dev/null | cut -d= -f2 || echo "us-central1")
# Firestore collection for quotes
QUOTES_COL ?= quotes
# Terraform directory
TF_DIR     := terraform

# ── Help ────────────────────────────────────────────────────────────────────

help: ## Show this help message
	@echo ""
	@echo "  ⚔️  Iron Counsel — available targets"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ── Infrastructure (Terraform) ───────────────────────────────────────────────

infra-init: ## Init Terraform with GCS backend. Usage: make infra-init BUCKET=my-tf-state-bucket
ifndef BUCKET
	$(error BUCKET is required. Usage: make infra-init BUCKET=my-tf-state-bucket)
endif
	cd $(TF_DIR) && terraform init -backend-config="bucket=$(BUCKET)" -reconfigure

infra-plan: ## Preview infrastructure changes
	cd $(TF_DIR) && terraform plan

infra-apply: ## Apply infrastructure changes (creates all GCP resources)
	cd $(TF_DIR) && terraform apply -auto-approve

infra-destroy: ## Destroy all Terraform-managed GCP resources
	@echo "⚠️  This will destroy all GCP resources. Press Ctrl-C to cancel, Enter to continue."
	@read _confirm
	cd $(TF_DIR) && terraform destroy -auto-approve

infra-output: ## Print all Terraform outputs (Cloud Run URL, WIF provider, etc.)
	cd $(TF_DIR) && terraform output

# ── Local Development ────────────────────────────────────────────────────────

setup: ## Copy .env.example → .env (if .env doesn't exist) and check prerequisites
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Created .env from .env.example — fill in your values before continuing."; \
	else \
		echo "ℹ️  .env already exists, skipping copy."; \
	fi
	@echo ""
	@echo "Checking prerequisites..."
	@command -v docker  >/dev/null || echo "  ❌ docker not found"
	@command -v uv      >/dev/null || echo "  ❌ uv not found"
	@command -v gcloud  >/dev/null || echo "  ❌ gcloud not found"
	@command -v terraform >/dev/null || echo "  ❌ terraform not found"
	@echo "  ✅ All checks done."

up: ## Build and start the local stack (Firestore emulator + app with hot-reload)
	docker compose up --build

down: ## Stop and remove local containers
	docker compose down

logs: ## Tail app container logs
	docker compose logs -f app

test: ## Run the test suite
	uv run pytest --tb=short -q

# ── Data Ingestion ───────────────────────────────────────────────────────────

_ingest_env  = GCP_PROJECT_ID=$(PROJECT_ID)
_ingest_emulator_env = FIRESTORE_EMULATOR_HOST=localhost:8081 $(_ingest_env)

kaggle-download: ## Download GoT dataset from Kaggle. Requires kaggle CLI + credentials.
	@command -v kaggle >/dev/null || (echo "❌ kaggle CLI not found. Install: pip install kaggle" && exit 1)
	kaggle datasets download -d $(DATASET) --unzip
	@echo "✅ Dataset downloaded. CSV files are in the current directory."

embed: ## Phase 1 — embed CSV → vectors.json using local fastembed/ONNX model (no API key needed)
ifndef CSV
	$(error CSV is required. Usage: make embed CSV=Game_of_Thrones_Script.csv)
endif
	@echo "ℹ️  Embedding $(CSV) → $(VECTORS_FILE) in batches of $(BATCH_SIZE)"
	GCP_PROJECT_ID=$(PROJECT_ID) EMBEDDING_MODEL_NAME=$(EMBEDDING_MODEL_NAME) \
		uv run python scripts/ingest.py \
			--csv $(CSV) --vectors-file $(VECTORS_FILE) \
			--batch-size $(BATCH_SIZE) --embed-only

docker-embed: ## Phase 1 — embed via Docker (for Intel Mac / unsupported platforms)
ifndef CSV
	$(error CSV is required. Usage: make docker-embed CSV=Game_of_Thrones_Script.csv)
endif
	@echo "ℹ️  Running embed inside Docker (Linux x86_64)..."
	docker run --rm \
		-v "$(PWD):/app" -w /app \
		-e GCP_PROJECT_ID=$(PROJECT_ID) \
		-e EMBEDDING_MODEL_NAME=$(EMBEDDING_MODEL_NAME) \
		python:3.13-slim sh -c \
		"pip install -q uv && uv sync --group embed && uv run --group embed python scripts/ingest.py --csv $(CSV) --vectors-file $(VECTORS_FILE) --batch-size $(BATCH_SIZE) --embed-only"

upload: ## Phase 2 — upload vectors.json → LOCAL Firestore emulator (emulator must be running)
	@echo "ℹ️  Uploading $(VECTORS_FILE) to local Firestore emulator"
	$(_ingest_emulator_env) \
		uv run python scripts/ingest.py --vectors-file $(VECTORS_FILE) --upload-only

upload-prod: ## Phase 2 — upload vectors.json → PRODUCTION Firestore
	@echo "⚠️  Uploading $(VECTORS_FILE) to PRODUCTION Firestore. Project: $(PROJECT_ID)"
	$(_ingest_env) \
		uv run python scripts/ingest.py --vectors-file $(VECTORS_FILE) --upload-only

ingest: ## Full pipeline (embed + upload) into the LOCAL Firestore emulator
ifndef CSV
	$(error CSV is required. Usage: make ingest CSV=Game_of_Thrones_Script.csv)
endif
	@echo "ℹ️  Ingesting into local Firestore emulator (FIRESTORE_EMULATOR_HOST=localhost:8081)"
	$(_ingest_emulator_env) \
		uv run python scripts/ingest.py \
			--csv $(CSV) --vectors-file $(VECTORS_FILE) \
			--batch-size $(BATCH_SIZE)

ingest-prod: ## Full pipeline (embed + upload) into PRODUCTION Firestore
ifndef CSV
	$(error CSV is required. Usage: make ingest-prod CSV=Game_of_Thrones_Script.csv)
endif
	@echo "⚠️  Ingesting into PRODUCTION Firestore. Project: $(PROJECT_ID)"
	$(_ingest_env) \
		uv run python scripts/ingest.py \
			--csv $(CSV) --vectors-file $(VECTORS_FILE) \
			--batch-size $(BATCH_SIZE)

vector-index: ## Create the Firestore vector index for the quotes collection (run once after infra-apply)
ifndef PROJECT_ID
	$(error GCP_PROJECT_ID not found. Set it in .env or pass: make vector-index PROJECT_ID=my-project)
endif
	@echo "Creating Firestore vector index on '$(QUOTES_COL)' collection..."
	gcloud firestore indexes composite create \
		--project=$(PROJECT_ID) \
		--collection-group=$(QUOTES_COL) \
		--query-scope=COLLECTION \
		--field-config=vector-config='{"dimension":"384","flat":"{}"}',field-path=embedding
	@echo "✅ Index creation started. Monitor progress: https://console.cloud.google.com/firestore/databases/-default-/indexes"

# ── Deployment Helpers ───────────────────────────────────────────────────────

webhook: ## Register the Telegram webhook using the Cloud Run URL from Terraform output
	$(eval SERVICE_URL := $(shell cd $(TF_DIR) && terraform output -raw cloud_run_url 2>/dev/null))
	$(eval TG_TOKEN    := $(shell grep -E '^TELEGRAM_TOKEN=' .env | cut -d= -f2))
	$(eval TG_SECRET   := $(shell grep -E '^TELEGRAM_WEBHOOK_SECRET=' .env | cut -d= -f2))
	@if [ -z "$(SERVICE_URL)" ]; then echo "❌ Could not read cloud_run_url from terraform output. Run 'make infra-apply' first."; exit 1; fi
	@echo "Registering webhook: $(SERVICE_URL)/webhook"
	curl -s -X POST "https://api.telegram.org/bot$(TG_TOKEN)/setWebhook" \
		-H "Content-Type: application/json" \
		-d "{\"url\": \"$(SERVICE_URL)/webhook\", \"secret_token\": \"$(TG_SECRET)\"}" | python3 -m json.tool
	@echo "✅ Webhook registered."

# ── Composite Workflows ───────────────────────────────────────────────────────

bootstrap: ## Full first-time setup: infra-apply → vector-index → webhook
	@echo "🚀 Starting Iron Counsel bootstrap..."
	@echo ""
	@echo "Step 1/3: Applying Terraform infrastructure..."
	$(MAKE) infra-apply
	@echo ""
	@echo "Step 2/3: Creating Firestore vector index..."
	$(MAKE) vector-index
	@echo ""
	@echo "Step 3/3: Registering Telegram webhook..."
	$(MAKE) webhook
	@echo ""
	@echo "✅ Bootstrap complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Download + ingest data: make kaggle-download && make ingest-prod CSV=Game_of_Thrones_Script.csv"
	@echo "  2. Test locally: make dev"
	@echo "  3. Push to GitHub to deploy: git push origin main"

dev: ## Set up .env (if needed) and start the local dev stack
	$(MAKE) setup
	$(MAKE) up
