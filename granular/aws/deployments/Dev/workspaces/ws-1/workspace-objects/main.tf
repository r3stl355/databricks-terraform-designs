locals {
  config = jsondecode(file("${path.root}/${var.var_file}"))
  cluster_params = local.config.cluster_params
  workpace_admin_params = local.config.workpace_admin_params
}

module "cluster" {
  source = "../../../../../modules/cluster"
  cluster_params = local.cluster_params  
  providers = {
    databricks.workspace = databricks.workspace
  } 
}

module "admin" {
  source = "../../../../../modules/workspace-admin"
  workpace_admin_params = local.workpace_admin_params  
  providers = {
    databricks.workspace = databricks.workspace
  } 
}