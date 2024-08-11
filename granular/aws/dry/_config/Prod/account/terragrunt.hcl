terraform {
  source = "../../../../../..//granular/aws/dry/account"
}

locals {
  var_file = get_env("TF_VAR_var_file", "variables.json")
}

inputs = {
  metastore_params = jsondecode(file("${get_terragrunt_dir()}/${local.var_file}"))
}