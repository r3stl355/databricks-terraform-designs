resource "aws_iam_role" "cross_account_role" {
  provider = aws.regional
  name               = "${var.workspace_params.workspace_name}-crossaccount"
  assume_role_policy = data.databricks_aws_assume_role_policy.main.json
  tags               = var.workspace_params.tags
}

resource "aws_iam_role_policy" "main" {
  provider = aws.regional
  name   = "${var.workspace_params.workspace_name}-policy"
  role   = aws_iam_role.cross_account_role.id
  policy = data.databricks_aws_crossaccount_policy.main.json
}