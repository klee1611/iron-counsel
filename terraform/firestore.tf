resource "google_firestore_database" "default" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# NOTE: Firestore vector index on the `quotes` collection cannot be managed
# by Terraform yet. After `terraform apply`, create it with:
#
#   gcloud firestore indexes composite create \
#     --project=<project_id> \
#     --collection-group=quotes \
#     --query-scope=COLLECTION \
#     --field-config=vector-config='{"dimension":"768","flat":"{}"}',field-path=embedding
#
# Index creation takes a few minutes. Monitor progress in GCP Console → Firestore → Indexes.
# ---------------------------------------------------------------------------
