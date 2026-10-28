resource "google_firestore_database" "default" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# NOTE: This repository creates the Firestore vector index manually after
# `terraform apply`. The indexed vectors and runtime query vectors are 384-dimensional.
# Inspect existing indexes first; if a replacement is needed, wait for the new index
# to become READY before deleting an old one.
#
#   gcloud firestore indexes composite list --project=<project_id> --database='(default)'
#
#   gcloud firestore indexes composite create \
#     --project=<project_id> \
#     --collection-group=quotes \
#     --query-scope=COLLECTION \
#     --field-config=field-path=embedding,vector-config='{"dimension":"384","flat":"{}"}'
#
# Index creation takes a few minutes. Monitor progress in GCP Console → Firestore → Indexes.
# ---------------------------------------------------------------------------
