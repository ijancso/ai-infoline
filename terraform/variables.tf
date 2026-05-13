variable "do_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "DigitalOcean region"
  type        = string
  default     = "nyc1"
}

variable "db_password" {
  description = "Password for the managed PostgreSQL database"
  type        = string
  sensitive   = true
}

variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
  default     = "ai-infoline"
}
