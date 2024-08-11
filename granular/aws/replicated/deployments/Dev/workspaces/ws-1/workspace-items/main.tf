locals {
  params                = jsondecode(file("${path.root}/${var.var_file}"))
  cluster_params        = local.params.cluster_params
  workpace_admin_params = local.params.workpace_admin_params
}

module "cluster" {
  source          = "../../../../../../../../modules/aws/cluster"
  cluster_params  = local.cluster_params  
  providers = {
    databricks.workspace = databricks.workspace
  } 
}

module "admin" {
  source                = "../../../../../../../../modules/aws/workspace-admin"
  workpace_admin_params = local.workpace_admin_params  
  providers = {
    databricks.workspace = databricks.workspace
  } 
}