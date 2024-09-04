terraform {
  source = "../../../../../../../..//granular/aws/dry/workspace"
}

locals {
  var_file_prefix   = get_env("TF_VAR_var_file_prefix", "")
  var_file          = "${local.var_file_prefix}variables.json"
}

inputs = {
  workspace_params = jsondecode(file("${get_terragrunt_dir()}/${local.var_file}"))
}