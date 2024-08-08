
output "workspace_url" {
  value = module.workspace.workspace_url
}

output "databricks_token" {
  value     = module.workspace.databricks_token
  sensitive = true
}