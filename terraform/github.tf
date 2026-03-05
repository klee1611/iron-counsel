# ---------------------------------------------------------------------------
# Sync Terraform outputs → GitHub Actions repository variables automatically.
# These are plain-text deployment identifiers (not secrets).
# ---------------------------------------------------------------------------

locals {
  repo_name = split("/", var.github_repo)[1]
  repo_owner = split("/", var.github_repo)[0]
}

resource "github_actions_variable" "gcp_project_id" {
  repository    = local.repo_name
  variable_name = "GCP_PROJECT_ID"
  value         = var.project_id
}

resource "github_actions_variable" "gcp_region" {
  repository    = local.repo_name
  variable_name = "GCP_REGION"
  value         = var.region
}

resource "github_actions_variable" "ar_repo" {
  repository    = local.repo_name
  variable_name = "AR_REPO"
  value         = "${var.region}-docker.pkg.dev/${var.project_id}/${var.ar_repository_id}"
}

resource "github_actions_variable" "cloud_run_service" {
  repository    = local.repo_name
  variable_name = "CLOUD_RUN_SERVICE"
  value         = var.cloud_run_service_name
}

resource "github_actions_variable" "wif_provider" {
  repository    = local.repo_name
  variable_name = "WIF_PROVIDER"
  value         = google_iam_workload_identity_pool_provider.github.name

  depends_on = [google_iam_workload_identity_pool_provider.github]
}

resource "github_actions_variable" "deploy_sa" {
  repository    = local.repo_name
  variable_name = "DEPLOY_SA"
  value         = google_service_account.deploy_sa.email

  depends_on = [google_service_account.deploy_sa]
}
