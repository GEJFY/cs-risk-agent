variable "project_name" {
  type    = string
  default = "csrisk"
}

variable "enable_azure" {
  type    = bool
  default = true
}

variable "enable_aws" {
  type    = bool
  default = false
}

variable "enable_gcp" {
  type    = bool
  default = false
}

variable "azure_tenant_id" {
  type    = string
  default = ""
}

variable "db_admin_password" {
  type      = string
  sensitive = true
  default   = ""
}

variable "gcp_project_id" {
  type    = string
  default = ""
}
