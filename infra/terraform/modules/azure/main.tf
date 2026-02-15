# =============================================================================
# Azure AI Foundry + 関連リソース
# =============================================================================

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }
}

# --- リソースグループ ---
resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-${var.environment}-rg"
  location = var.location
  tags     = var.tags
}

# --- Azure OpenAI Service ---
resource "azurerm_cognitive_account" "openai" {
  name                  = "${var.project_name}-${var.environment}-openai"
  location              = var.location
  resource_group_name   = azurerm_resource_group.main.name
  kind                  = "OpenAI"
  sku_name              = "S0"
  custom_subdomain_name = "${var.project_name}-${var.environment}"

  network_acls {
    default_action = "Deny"
    ip_rules       = var.allowed_ip_ranges
  }

  tags = var.tags
}

# --- GPT-4o デプロイメント (SOTA) ---
resource "azurerm_cognitive_deployment" "gpt4o" {
  name                 = "gpt-4o"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-11-20"
  }

  sku {
    name     = "Standard"
    capacity = var.sota_model_capacity
  }
}

# --- GPT-4o-mini デプロイメント (Cost Effective) ---
resource "azurerm_cognitive_deployment" "gpt4o_mini" {
  name                 = "gpt-4o-mini"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-4o-mini"
    version = "2024-07-18"
  }

  sku {
    name     = "Standard"
    capacity = var.cost_effective_model_capacity
  }
}

# --- Key Vault (シークレット管理) ---
resource "azurerm_key_vault" "main" {
  name                        = "${var.project_name}-${var.environment}-kv"
  location                    = var.location
  resource_group_name         = azurerm_resource_group.main.name
  tenant_id                   = var.tenant_id
  sku_name                    = "standard"
  soft_delete_retention_days  = 90
  purge_protection_enabled    = true
  enable_rbac_authorization   = true

  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"
    ip_rules       = var.allowed_ip_ranges
  }

  tags = var.tags
}

# --- OpenAI API キーを Key Vault に保存 ---
resource "azurerm_key_vault_secret" "openai_key" {
  name         = "openai-api-key"
  value        = azurerm_cognitive_account.openai.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
}

# --- App Service Plan ---
resource "azurerm_service_plan" "main" {
  name                = "${var.project_name}-${var.environment}-plan"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  os_type             = "Linux"
  sku_name            = var.app_service_sku

  tags = var.tags
}

# --- App Service (Backend) ---
resource "azurerm_linux_web_app" "backend" {
  name                = "${var.project_name}-${var.environment}-api"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  service_plan_id     = azurerm_service_plan.main.id

  site_config {
    application_stack {
      docker_image_name   = "${var.container_registry}/${var.project_name}-backend:latest"
    }
    always_on = var.environment == "prod"
  }

  app_settings = {
    "AZURE_AI_ENDPOINT"    = azurerm_cognitive_account.openai.endpoint
    "AZURE_AI_API_VERSION" = "2024-12-01-preview"
    "APP_ENV"              = var.environment
    "KEY_VAULT_URI"        = azurerm_key_vault.main.vault_uri
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# --- PostgreSQL Flexible Server ---
resource "azurerm_postgresql_flexible_server" "main" {
  name                          = "${var.project_name}-${var.environment}-db"
  location                      = var.location
  resource_group_name           = azurerm_resource_group.main.name
  version                       = "16"
  administrator_login           = var.db_admin_username
  administrator_password        = var.db_admin_password
  storage_mb                    = var.db_storage_mb
  sku_name                      = var.db_sku_name
  backup_retention_days         = 30
  geo_redundant_backup_enabled  = var.environment == "prod"
  zone                          = "1"

  tags = var.tags
}

resource "azurerm_postgresql_flexible_server_database" "app" {
  name      = "cs_risk_agent"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "ja_JP.utf8"
}

# --- Redis Cache ---
resource "azurerm_redis_cache" "main" {
  name                = "${var.project_name}-${var.environment}-redis"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  capacity            = var.redis_capacity
  family              = var.redis_family
  sku_name            = var.redis_sku
  minimum_tls_version = "1.2"

  redis_configuration {
    maxmemory_policy = "allkeys-lru"
  }

  tags = var.tags
}
