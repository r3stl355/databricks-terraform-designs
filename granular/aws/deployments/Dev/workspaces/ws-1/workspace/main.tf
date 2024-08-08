locals {
  workspace_params = jsondecode(file("${path.root}/${var.var_file}"))
  account_params = jsondecode(var.account_params)
}

module "workspace" {
  source = "../../../../../modules/workspace"
  account_params    = local.account_params
  workspace_params  = local.workspace_params
  providers = {
    databricks.account = databricks.account
  } 
}