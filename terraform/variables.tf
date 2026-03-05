variable "github_token" {
  description = "GitHub Personal Access Token with repo scope — used to sync Terraform outputs to Actions variables"
  type        = string
  sensitive   = true
}

variable "groq_api_key" {
  description = "Groq API key for LLaMA 3.3 70B inference — https://console.groq.com"
  type        = string
  sensitive   = true
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for all resources"
  type        = string
  default     = "us-central1"
}

variable "tf_state_bucket" {
  description = "GCS bucket name for Terraform remote state (must exist before terraform init)"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository in 'owner/repo' format, used to scope Workload Identity Federation"
  type        = string
}

variable "telegram_token" {
  description = "Telegram bot token from BotFather"
  type        = string
  sensitive   = true
}

variable "telegram_webhook_secret" {
  description = "Random secret to validate incoming Telegram webhook requests"
  type        = string
  sensitive   = true
}

variable "cloud_run_service_name" {
  description = "Name of the Cloud Run service"
  type        = string
  default     = "iron-counsel"
}

variable "ar_repository_id" {
  description = "Artifact Registry repository ID for Docker images"
  type        = string
  default     = "iron-counsel"
}

variable "allowed_user_ids" {
  description = "Comma-separated Telegram user IDs allowed to use the bot. Leave empty to allow everyone."
  type        = string
  default     = ""
}
