resource "google_artifact_registry_repository" "iron_counsel" {
  project       = var.project_id
  location      = var.region
  repository_id = var.ar_repository_id
  format        = "DOCKER"
  description   = "Docker images for Iron Counsel"

  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "keep-latest"
    action = "KEEP"
    most_recent_versions {
      keep_count = 1
    }
  }

  cleanup_policies {
    id     = "delete-old"
    action = "DELETE"
    condition {
      tag_state = "ANY"
    }
  }

  depends_on = [google_project_service.apis]
}
