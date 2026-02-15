# =============================================================================
# Development 環境
# =============================================================================

terraform {
  required_version = ">= 1.9.0"

  backend "local" {
    path = "terraform.tfstate"
  }
}

# --- Azure Module ---
module "azure" {
  source      = "../../modules/azure"
  count       = var.enable_azure ? 1 : 0

  project_name     = var.project_name
  environment      = "dev"
  location         = "japaneast"
  tenant_id        = var.azure_tenant_id
  db_admin_password = var.db_admin_password

  app_service_sku               = "B1"
  sota_model_capacity           = 10
  cost_effective_model_capacity = 30
  db_sku_name                   = "B_Standard_B1ms"
  redis_capacity                = 0
  redis_sku                     = "Basic"

  tags = {
    project     = var.project_name
    environment = "dev"
    managed     = "terraform"
  }
}

# --- AWS Module ---
module "aws" {
  source = "../../modules/aws"
  count  = var.enable_aws ? 1 : 0

  project_name = var.project_name
  environment  = "dev"
  region       = "us-east-1"
  task_cpu     = "256"
  task_memory  = "512"

  tags = {
    project     = var.project_name
    environment = "dev"
    managed     = "terraform"
  }
}

# --- GCP Module ---
module "gcp" {
  source = "../../modules/gcp"
  count  = var.enable_gcp ? 1 : 0

  project_name = var.project_name
  project_id   = var.gcp_project_id
  environment  = "dev"
  region       = "us-central1"

  cloud_run_cpu    = "1"
  cloud_run_memory = "512Mi"
  max_instances    = 2
  db_tier          = "db-f1-micro"
  redis_memory_gb  = 1

  labels = {
    project     = var.project_name
    environment = "dev"
    managed     = "terraform"
  }
}
