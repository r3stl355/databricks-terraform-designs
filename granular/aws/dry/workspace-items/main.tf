module "cluster" {
  source          = "../../../../modules/aws/cluster"
  cluster_params  = var.cluster_params  
  providers = {
    databricks.workspace = databricks.workspace
  } 
}

module "admin" {
  source                = "../../../../modules/aws/workspace-admin"
  workpace_admin_params = var.workpace_admin_params  
  providers = {
    databricks.workspace = databricks.workspace
  } 
}