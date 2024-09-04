terraform {
  source = "../../../../../../../..//granular/aws/dry/workspace"
}

include "backend" {
  path    = find_in_parent_folders("backend.hcl")
  expose  = true
}

locals {
  var_file_prefix   = get_env("TF_VAR_var_file_prefix", "")
  var_file          = "${local.var_file_prefix}variables.json"
  params            = jsondecode(file("${get_terragrunt_dir()}/${local.var_file}"))
  remote_config     = include.backend.remote_state.config
}

inputs = {
  workspace_params            = local.params.workspace_params
  account_remote_state_params = merge(local.remote_config, local.params.account_remote_state_params)
}