variable "project_name" {
  type    = string
  default = "csrisk"
}

variable "project_id" {
  type = string
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "labels" {
  type = map(string)
  default = {
    project = "cs-risk-agent"
    managed = "terraform"
  }
}

variable "artifact_registry_url" {
  type    = string
  default = ""
}

variable "cloud_run_cpu" {
  type    = string
  default = "1"
}

variable "cloud_run_memory" {
  type    = string
  default = "512Mi"
}

variable "max_instances" {
  type    = number
  default = 3
}

variable "db_tier" {
  type    = string
  default = "db-f1-micro"
}

variable "vpc_network_id" {
  type    = string
  default = ""
}

variable "redis_memory_gb" {
  type    = number
  default = 1
}
