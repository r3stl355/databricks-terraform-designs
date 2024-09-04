provider "databricks" {
  alias         = "workspace"
  host          = data.terraform_remote_state.workspace.outputs.workspace_url
  token         = data.terraform_remote_state.workspace.outputs.databricks_token
}