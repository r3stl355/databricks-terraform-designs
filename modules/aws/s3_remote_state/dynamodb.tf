resource "aws_dynamodb_table" "basic-dynamodb-table" {
  count           = var.s3_remote_state_params.dynamodb_table_name == null ? 0 : 1
  name            = var.s3_remote_state_params.dynamodb_table_name
  billing_mode    = "PROVISIONED"
  read_capacity   = 1
  write_capacity  = 1
  hash_key        = "LockID"
  attribute {
    name = "LockID"
    type = "S"
  }
  tags            = local.tags
}