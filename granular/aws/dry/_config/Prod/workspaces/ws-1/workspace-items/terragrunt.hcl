terraform {
  source = "../../../../../../../..//granular/aws/dry/workspace-items"
}

locals {
  var_file  = get_env("TF_VAR_var_file", "variables.json")
  params    = jsondecode(file("${get_terragrunt_dir()}/${local.var_file}"))
  
  workspace_url         = local.params.workspace_url
  cluster_params        = local.params.cluster_params
  workpace_admin_params = local.params.workpace_admin_params
}

inputs = { 
  workspace_url         = local.workspace_url
  cluster_params        = local.cluster_params
  workpace_admin_params = local.workpace_admin_params
}