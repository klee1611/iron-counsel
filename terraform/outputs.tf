output "cloud_run_url" {
  description = "Publicly accessible URL of the Cloud Run service (use as Telegram webhook URL + /webhook)"
  value       = google_cloud_run_v2_service.iron_counsel.uri
}

output "artifact_registry_repo" {
  description = "Full Artifact Registry repository path for Docker images (use in deploy workflow)"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.ar_repository_id}"
}

output "workload_identity_provider" {
  description = "Full WIF provider resource name — set as GHA variable WIF_PROVIDER"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "deploy_service_account" {
  description = "Email of the deploy service account — set as GHA variable DEPLOY_SA"
  value       = google_service_account.deploy_sa.email
}

output "cloud_run_service_name" {
  description = "Cloud Run service name — set as GHA variable CLOUD_RUN_SERVICE"
  value       = google_cloud_run_v2_service.iron_counsel.name
}
