resource "aws_s3_bucket" "root_storage_bucket" {
  provider = aws.regional
  bucket        = "${var.workspace_params.workspace_name}-rootbucket"
  force_destroy = true
  tags = merge(var.workspace_params.tags, {
    Name = "${var.workspace_params.workspace_name}-rootbucket"
  })
}

resource "aws_s3_bucket_versioning" "versioning" {
  provider = aws.regional
  bucket = aws_s3_bucket.root_storage_bucket.id
  versioning_configuration {
    status = "Disabled"
  }
}

resource "aws_s3_bucket_ownership_controls" "state" {
  provider = aws.regional
  bucket = aws_s3_bucket.root_storage_bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "acl" {
  provider = aws.regional
  bucket     = aws_s3_bucket.root_storage_bucket.id
  acl        = "private"
  depends_on = [aws_s3_bucket_ownership_controls.state]
}

resource "aws_s3_bucket_server_side_encryption_configuration" "root_storage_bucket" {
  provider = aws.regional
  bucket = aws_s3_bucket.root_storage_bucket.bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "root_storage_bucket" {
  provider = aws.regional
  bucket                  = aws_s3_bucket.root_storage_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "root_bucket_policy" {
  provider = aws.regional
  bucket     = aws_s3_bucket.root_storage_bucket.id
  policy     = data.databricks_aws_bucket_policy.root.json
  depends_on = [aws_s3_bucket_public_access_block.root_storage_bucket]
}
