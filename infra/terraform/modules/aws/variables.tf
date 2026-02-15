variable "project_name" {
  type    = string
  default = "csrisk"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "tags" {
  type = map(string)
  default = {
    project = "cs-risk-agent"
    managed = "terraform"
  }
}

variable "ecr_repository_url" {
  type    = string
  default = ""
}

variable "task_cpu" {
  type    = string
  default = "512"
}

variable "task_memory" {
  type    = string
  default = "1024"
}

variable "database_url" {
  type      = string
  sensitive = true
  default   = ""
}

variable "redis_url" {
  type      = string
  sensitive = true
  default   = ""
}

variable "jwt_secret" {
  type      = string
  sensitive = true
  default   = ""
}
