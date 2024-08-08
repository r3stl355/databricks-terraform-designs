locals {
  metastore_params = jsondecode(file("${path.root}/${var.var_file}"))
  account_params = jsondecode(var.account_params)
}

module "metastore" {
  source = "../../../modules/metastore"
  account_params    = local.account_params
  metastore_params  = local.metastore_params
  providers = {
    databricks.account = databricks.account
  } 
}