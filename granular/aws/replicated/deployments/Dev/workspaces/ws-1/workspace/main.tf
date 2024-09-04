locals {
  var_file_prefix   = var.var_file_prefix
  var_file          = "${local.var_file_prefix}variables.json"
  params            = jsondecode(file("${path.root}/${local.var_file}"))
  account_params    = jsondecode(var.account_params)
  wsp               = local.params.workspace_params
  workspace_params  = local.wsp.metastore_id == null ? merge(local.wsp,  { metastore_id = [for m_name, m_id in data.terraform_remote_state.account.outputs.metastores: m_id if m_name == local.wsp.metastore_name ][0]}) : local.wsp
}

module "workspace" {
  source            = "../../../../../../../../modules/aws/workspace"
  account_params    = local.account_params
  workspace_params  = local.workspace_params
  providers         = {
    databricks.account  = databricks.account
    aws.regional        = aws
  } 
}