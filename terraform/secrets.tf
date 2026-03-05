resource "google_secret_manager_secret" "groq_api_key" {
  project   = var.project_id
  secret_id = "groq-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "groq_api_key" {
  secret      = google_secret_manager_secret.groq_api_key.id
  secret_data = var.groq_api_key
}

resource "google_secret_manager_secret" "telegram_token" {
  project   = var.project_id
  secret_id = "telegram-token"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "telegram_token" {
  secret      = google_secret_manager_secret.telegram_token.id
  secret_data = var.telegram_token
}

resource "google_secret_manager_secret" "telegram_webhook_secret" {
  project   = var.project_id
  secret_id = "telegram-webhook-secret"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "telegram_webhook_secret" {
  secret      = google_secret_manager_secret.telegram_webhook_secret.id
  secret_data = var.telegram_webhook_secret
}
