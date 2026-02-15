variable "project_name" {
  description = "プロジェクト名"
  type        = string
  default     = "csrisk"
}

variable "environment" {
  description = "環境 (dev/staging/prod)"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure リージョン"
  type        = string
  default     = "japaneast"
}

variable "tenant_id" {
  description = "Azure AD テナントID"
  type        = string
}

variable "tags" {
  description = "リソースタグ"
  type        = map(string)
  default = {
    project = "cs-risk-agent"
    managed = "terraform"
  }
}

variable "allowed_ip_ranges" {
  description = "許可IPレンジ"
  type        = list(string)
  default     = []
}

variable "sota_model_capacity" {
  description = "SOTAモデルのTPMキャパシティ"
  type        = number
  default     = 30
}

variable "cost_effective_model_capacity" {
  description = "コスパモデルのTPMキャパシティ"
  type        = number
  default     = 60
}

variable "app_service_sku" {
  description = "App Service SKU"
  type        = string
  default     = "B1"
}

variable "container_registry" {
  description = "コンテナレジストリURL"
  type        = string
  default     = ""
}

variable "db_admin_username" {
  description = "PostgreSQL管理者ユーザー名"
  type        = string
  default     = "csriskadmin"
  sensitive   = true
}

variable "db_admin_password" {
  description = "PostgreSQL管理者パスワード"
  type        = string
  sensitive   = true
}

variable "db_storage_mb" {
  description = "PostgreSQLストレージ(MB)"
  type        = number
  default     = 32768
}

variable "db_sku_name" {
  description = "PostgreSQL SKU"
  type        = string
  default     = "B_Standard_B1ms"
}

variable "redis_capacity" {
  description = "Redis キャパシティ"
  type        = number
  default     = 0
}

variable "redis_family" {
  description = "Redis ファミリー"
  type        = string
  default     = "C"
}

variable "redis_sku" {
  description = "Redis SKU"
  type        = string
  default     = "Basic"
}
