locals {
  var_file_prefix       = var.var_file_prefix
  var_file              = "${local.var_file_prefix}variables.json"
  params                = jsondecode(file("${path.root}/${local.var_file}"))
  cluster_params        = local.params.cluster_params
  workpace_admin_params = local.params.workpace_admin_params
}

module "cluster" {
  source          = "../../../../../../../../modules/cluster"
  cluster_params  = local.cluster_params
  providers = {
    databricks.workspace = databricks.workspace
  } 
}

module "admin" {
  source                = "../../../../../../../../modules/workspace-admin"
  workpace_admin_params = local.workpace_admin_params  
  providers = {
    databricks.workspace = databricks.workspace
  } 
}