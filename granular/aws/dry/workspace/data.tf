data "terraform_remote_state" "account" {
  backend = "s3" 
  config = {
    region      = var.account_remote_state_params.region
    bucket      = var.account_remote_state_params.bucket
    key         = var.account_remote_state_params.key
    kms_key_id  = var.account_remote_state_params.kms_key_id
  }
}