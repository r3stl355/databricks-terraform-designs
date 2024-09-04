locals {
  var_file_prefix   = var.var_file_prefix
  var_file          = "${local.var_file_prefix}variables.json"
  params            = jsondecode(file("${path.root}/${local.var_file}"))
}

module "s3_remote_state" {
  source                  = "../../../../modules/aws/s3_remote_state"
  s3_remote_state_params  = local.params.s3_remote_state_params
  providers = {
    aws.regional  = aws
  }
}