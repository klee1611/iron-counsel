# ---------------------------------------------------------------------------
# Service Account: Cloud Run runtime
# ---------------------------------------------------------------------------

resource "google_service_account" "cloud_run_sa" {
  project      = var.project_id
  account_id   = "iron-counsel-run-sa"
  display_name = "Iron Counsel Cloud Run SA"
}

resource "google_project_iam_member" "run_sa_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_project_iam_member" "run_sa_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# ---------------------------------------------------------------------------
# Service Account: GitHub Actions deploy (impersonated via WIF)
# ---------------------------------------------------------------------------

resource "google_service_account" "deploy_sa" {
  project      = var.project_id
  account_id   = "iron-counsel-deploy-sa"
  display_name = "Iron Counsel GitHub Actions Deploy SA"
}

resource "google_project_iam_member" "deploy_sa_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.deploy_sa.email}"
}

resource "google_project_iam_member" "deploy_sa_ar_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.deploy_sa.email}"
}

# deploy_sa must be able to act-as cloud_run_sa when deploying Cloud Run
resource "google_service_account_iam_member" "deploy_sa_act_as_run_sa" {
  service_account_id = google_service_account.cloud_run_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deploy_sa.email}"
}

# ---------------------------------------------------------------------------
# Service Account: GitHub Actions ingest (same deploy SA, needs Firestore + Vertex AI)
# Reuses deploy_sa — those roles already cover Firestore and Vertex AI indirectly.
# Add explicit Vertex AI + Firestore bindings to deploy_sa for ingest workflow.
# ---------------------------------------------------------------------------

resource "google_project_iam_member" "deploy_sa_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.deploy_sa.email}"
}
