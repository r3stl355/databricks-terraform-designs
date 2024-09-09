resource "aws_s3_bucket" "state" {
  provider      = aws.regional
  bucket        = var.s3_remote_state_params.bucket_name
  force_destroy = true
  tags          = local.tags
}

resource "aws_s3_bucket_versioning" "state" {
  provider  = aws.regional
  bucket    = aws_s3_bucket.state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_ownership_controls" "state" {
  provider  = aws.regional
  bucket    = aws_s3_bucket.state.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "acl" {
  provider    = aws.regional
  bucket      = aws_s3_bucket.state.id
  acl         = "private"
  depends_on  = [aws_s3_bucket_ownership_controls.state]
}

resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  count     = var.s3_remote_state_params.add_kms_key ? 1 : 0
  provider  = aws.regional
  bucket    = aws_s3_bucket.state.bucket

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.state[0].arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "main" {
  provider                = aws.regional
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

/*
resource "aws_s3_bucket_policy" "main" {
  provider    = aws.regional
  bucket      = aws_s3_bucket.root_storage_bucket.id
  policy      = <todo>
  depends_on  = [aws_s3_bucket_public_access_block.root_storage_bucket]
}
*/
