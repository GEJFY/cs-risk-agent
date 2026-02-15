# =============================================================================
# Azure IAM - 最小権限の原則
# =============================================================================

# App Service -> Key Vault アクセス
resource "azurerm_role_assignment" "app_keyvault_reader" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_web_app.backend.identity[0].principal_id
}

# App Service -> OpenAI アクセス
resource "azurerm_role_assignment" "app_openai_user" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_linux_web_app.backend.identity[0].principal_id
}

# App Service -> PostgreSQL アクセス (AAD認証時)
resource "azurerm_role_assignment" "app_db_contributor" {
  scope                = azurerm_postgresql_flexible_server.main.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_linux_web_app.backend.identity[0].principal_id
}
