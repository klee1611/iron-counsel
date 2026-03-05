resource "google_artifact_registry_repository" "iron_counsel" {
  project       = var.project_id
  location      = var.region
  repository_id = var.ar_repository_id
  format        = "DOCKER"
  description   = "Docker images for Iron Counsel"

  depends_on = [google_project_service.apis]
}
