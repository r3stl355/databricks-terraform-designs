terraform {
  source = "../../../../../../../..//granular/aws/dry/workspace-items"
}

include "backend" {
  path    = find_in_parent_folders("backend.hcl")
  expose  = true
}

locals {
  var_file_prefix       = get_env("TF_VAR_var_file_prefix", "")
  var_file              = "${local.var_file_prefix}variables.json"
  params                = jsondecode(file("${get_terragrunt_dir()}/${local.var_file}"))
  remote_config         = include.backend.remote_state.config
  cluster_params        = local.params.cluster_params
  workpace_admin_params = local.params.workpace_admin_params
}

inputs = {
  cluster_params                = local.cluster_params
  workpace_admin_params         = local.workpace_admin_params
  workspace_remote_state_params = merge(local.remote_config, local.params.workspace_remote_state_params)
}