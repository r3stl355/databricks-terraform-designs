data "aws_caller_identity" "current" {}

locals {
  tags = merge(var.s3_remote_state_params.tags, {
    Purpose = "Terraform-State-Management"
  })
}