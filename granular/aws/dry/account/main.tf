locals {
  account_params = jsondecode(var.account_params)
}

module "metastore" {
  source            = "../../../../modules/aws/metastore"
  metastore_params  = var.metastore_params
  providers = {
    databricks.account = databricks.account
  } 
}