terraform {
  source = "../../../../../..//granular/aws/dry/account"
}

locals {
  var_file_prefix   = get_env("TF_VAR_var_file_prefix", "")
  var_file          = "${local.var_file_prefix}variables.json"
  params            = jsondecode(file("${get_terragrunt_dir()}/${local.var_file}"))
}

include "backend" {
  path = find_in_parent_folders("${local.var_file_prefix}backend.hcl")
}

inputs = {
  metastore_params  = local.params.metastore_params
}