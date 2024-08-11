locals {
  params = jsondecode(file("${path.root}/${var.var_file}"))
  account_params        = jsondecode(var.account_params)
  metastore_params      = local.params.metastores
  workspace_params = { for k, v in local.params.workspaces:
    k => merge(v,  { metastore_id = [for m_name, m_id in module.metastore.metastores: m_id if m_name == v.metastore_id ][0]})
  }
}

module "metastore" {
  
  source = "../../../../../modules/aws/metastore"
  metastore_params  = local.metastore_params
  providers = {
    databricks.account = databricks.account
  } 
}

# First workspace

module "ws_1" {
  source = "../../../../../modules/aws/workspace"
  account_params    = local.account_params
  workspace_params  = local.workspace_params.ws_1
  providers = {
    databricks.account  = databricks.account
    aws.regional        = aws.ws_1
  } 
}

module "ws_1_cluster" {
  source = "../../../../../modules/aws/cluster"
  cluster_params = local.workspace_params.ws_1.cluster_params  
  providers = {
    databricks.workspace = databricks.ws_1
  } 
  depends_on = [module.ws_1]
}

module "ws_1_admin" {
  source = "../../../../../modules/aws/workspace-admin"
  workpace_admin_params = local.workspace_params.ws_1.workpace_admin_params  
  providers = {
    databricks.workspace = databricks.ws_1
  } 
  depends_on = [module.ws_1]
}

# Second workspace

module "ws_2" {
  source = "../../../../../modules/aws/workspace"
  account_params    = local.account_params
  workspace_params  = local.workspace_params.ws_2
  providers = {
    databricks.account  = databricks.account
    aws.regional        = aws.ws_2
  } 
}

module "ws_2_cluster" {
  source = "../../../../../modules/aws/cluster"
  cluster_params = local.workspace_params.ws_2.cluster_params  
  providers = {
    databricks.workspace = databricks.ws_2
  } 
  depends_on = [module.ws_2]
}

module "ws_2_admin" {
  source = "../../../../../modules/aws/workspace-admin"
  workpace_admin_params = local.workspace_params.ws_2.workpace_admin_params  
  providers = {
    databricks.workspace = databricks.ws_2
  } 
  depends_on = [module.ws_2]
}