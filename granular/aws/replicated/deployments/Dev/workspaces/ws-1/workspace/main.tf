locals {
  var_file_prefix   = var.var_file_prefix
  var_file          = "${local.var_file_prefix}variables.json"
  params            = jsondecode(file("${path.root}/${local.var_file}"))
  account_params    = jsondecode(var.account_params)

  wsp = local.params.workspace_params
  workspace_params  = merge(local.wsp,  { metastore_id = [for m_name, m_id in data.terraform_remote_state.account.outputs.metastores: m_id if m_name == local.wsp.metastore_id ][0]})

  /*
  workspace_params  = { for k, v in local.params.workspace_params:
    k => merge(v,  { metastore_id = [for m_name, m_id in data.terraform_remote_state.account.outputs.metastores: m_id if m_name == v.metastore_id ][0]})
  }
  */
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