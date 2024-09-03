resource "aws_kms_key" "state" {
  provider                = aws.regional
  description             = "Symmetric encryption KMS key for Terraform state encryption"
  enable_key_rotation     = false
  deletion_window_in_days = 10
  policy      = jsonencode({
    Version = "2012-10-17"
    Id      = "state-key-policy"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
        AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        },
        Action   = "kms:*"
        Resource = "*"
      }
    ]
  })
  tags = local.tags
}