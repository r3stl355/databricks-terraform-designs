locals {
  var_file_prefix   = var.var_file_prefix
  var_file          = "${local.var_file_prefix}variables.json"
  metastore_params  = jsondecode(file("${path.root}/${local.var_file}"))
  account_params    = jsondecode(var.account_params)
}

module "metastore" {
  source            = "../../../../../../modules/metastore"
  metastore_params  = local.metastore_params
  providers = {
    databricks.account = databricks.account
  } 
}