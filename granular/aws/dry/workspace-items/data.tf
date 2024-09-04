data "terraform_remote_state" "workspace" {
  backend = "s3" 
  config = {
    region      = var.workspace_remote_state_params.region
    bucket      = var.workspace_remote_state_params.bucket
    key         = var.workspace_remote_state_params.key
    kms_key_id  = var.workspace_remote_state_params.kms_key_id
  }
}