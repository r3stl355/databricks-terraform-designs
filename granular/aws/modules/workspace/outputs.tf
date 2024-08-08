
output "workspace_url" {
  value = databricks_mws_workspaces.main.workspace_url
}

output "databricks_token" {
  value     = databricks_mws_workspaces.main.token[0].token_value
  sensitive = true
}

output "workspace_id" {
  value = databricks_mws_workspaces.main.workspace_id
}