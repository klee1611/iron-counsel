locals {
  # Full Artifact Registry image path used as placeholder; replaced on first deploy
  placeholder_image = "us-docker.pkg.dev/cloudrun/container/hello"
}

resource "google_cloud_run_v2_service" "iron_counsel" {
  project             = var.project_id
  name                = var.cloud_run_service_name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.cloud_run_sa.email

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    containers {
      image = local.placeholder_image

      ports {
        container_port = 8080
      }

      # Non-secret env vars
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "ALLOWED_USER_IDS"
        value = var.allowed_user_ids
      }

      # Secret env vars sourced from Secret Manager
      env {
        name = "GROQ_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.groq_api_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "TELEGRAM_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.telegram_token.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "TELEGRAM_WEBHOOK_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.telegram_webhook_secret.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_secret_manager_secret_version.groq_api_key,
    google_secret_manager_secret_version.telegram_token,
    google_secret_manager_secret_version.telegram_webhook_secret,
  ]

  # Ignore image changes: the deploy workflow owns the image, not Terraform
  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }
}

# Allow unauthenticated (public) invocations — required for Telegram webhook
resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.iron_counsel.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
