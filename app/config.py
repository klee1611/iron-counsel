from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telegram
    telegram_token: str
    telegram_webhook_secret: str = ""

    # Allowlist of Telegram user IDs permitted to use the bot.
    # Set as a comma-separated string: "123456789,987654321"
    # If empty, all users are allowed.
    allowed_user_ids: str = ""

    @property
    def allowed_user_id_list(self) -> list[int]:
        """Parse comma-separated allowed_user_ids into a list of ints."""
        return [int(x.strip()) for x in self.allowed_user_ids.split(",") if x.strip()]

    # Groq API (LLM)
    groq_api_key: str

    # Google AI Studio API key (embeddings) - removed, using local HuggingFace model

    # GCP (Firestore only)
    gcp_project_id: str

    # Firestore collections
    firestore_quotes_collection: str = "quotes"
    firestore_conversations_collection: str = "conversations"

    # Model settings
    llm_model_name: str = "llama-3.3-70b-versatile"
    embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    retriever_top_k: int = 5
    conversation_history_limit: int = 10


settings = Settings()
