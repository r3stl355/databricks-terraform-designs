remote_state {
  backend = "s3"
  config = {
    region          = "eu-west-1"
    bucket          = "db-tf-remote-state"
    key             = "tf-state/${path_relative_to_include()}/terraform.tfstate"
    kms_key_id      = "<KMS-key-here-if-used>"
    dynamodb_table  = "db-tf-remote-state-lock"
  }
}