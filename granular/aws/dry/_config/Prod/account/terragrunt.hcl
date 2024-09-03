terraform {
  source = "../../../../../..//granular/aws/dry/account"
}

locals {
  var_file  = get_env("TF_VAR_var_file", "variables.json")
  params    = jsondecode(file("${get_terragrunt_dir()}/${local.var_file}"))
}

include "remote" {
  path = find_in_parent_folders("remote.hcl")
}

inputs = {
  metastore_params  = local.params.metastore_params
}