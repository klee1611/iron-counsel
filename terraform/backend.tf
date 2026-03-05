# ---------------------------------------------------------------------------
# GCS remote state
#
# IMPORTANT: The GCS bucket must be created BEFORE running `terraform init`.
# Create it once manually:
#   gcloud storage buckets create gs://<bucket-name> \
#     --project=<project-id> \
#     --location=<region> \
#     --uniform-bucket-level-access
# ---------------------------------------------------------------------------

terraform {
  backend "gcs" {
    # bucket is supplied via -backend-config or terraform.tfbackend file
    # to avoid committing the bucket name here.
    # Example:
    #   terraform init -backend-config="bucket=my-tf-state-bucket"
    # Or create a terraform.tfbackend file (gitignored):
    #   bucket = "my-tf-state-bucket"
    prefix = "iron-counsel/state"
  }
}
