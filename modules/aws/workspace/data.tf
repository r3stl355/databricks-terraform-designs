data "databricks_aws_assume_role_policy" "main" {
  external_id = var.account_params.account_id
}

data "databricks_aws_crossaccount_policy" "main" {}

data "aws_availability_zones" "available" {
  provider = aws.regional
}

data "databricks_aws_bucket_policy" "root" {
  bucket = aws_s3_bucket.root_storage_bucket.bucket
}