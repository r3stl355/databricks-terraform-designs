locals {
  account_params = jsondecode(var.account_params)
}

module "metastore" {
  source = "../../modules/metastore"
  account_params    = local.account_params
  metastore_params  = var.metastore_params
  providers = {
    databricks.account = databricks.account
  } 
}