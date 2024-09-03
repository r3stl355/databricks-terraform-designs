locals {
  params = jsondecode(file("${path.root}/${var.var_file}"))
}

module "s3_remote_state" {
  source                  = "../../../../modules/aws/s3_remote_state"
  s3_remote_state_params  = local.params.s3_remote_state_params
  providers = {
    aws.regional  = aws
  }
}