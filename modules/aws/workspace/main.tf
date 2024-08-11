resource "databricks_mws_networks" "main" {
  provider            = databricks.account
  account_id          = var.account_params.account_id
  network_name         = "${var.workspace_params.workspace_name}-network"
  security_group_ids  = [module.vpc.default_security_group_id]
  subnet_ids          = module.vpc.private_subnets
  vpc_id              = module.vpc.vpc_id
}

resource "databricks_mws_storage_configurations" "main" {
  provider                    = databricks.account
  account_id                  = var.account_params.account_id
  bucket_name                 = aws_s3_bucket.root_storage_bucket.bucket
  storage_configuration_name  = "${var.workspace_params.workspace_name}-storage"
}

resource "databricks_mws_credentials" "main" {
  provider          = databricks.account
  role_arn          = aws_iam_role.cross_account_role.arn
  credentials_name  = "${var.workspace_params.workspace_name}-creds"
  depends_on        = [time_sleep.wait]
}

# Adding a wait timer to reduce the chance of `Failed credential validation check` error
resource "time_sleep" "wait" {
  create_duration = "30s"
  depends_on = [
    aws_iam_role_policy.main
  ]
}

resource "databricks_mws_workspaces" "main" {
  provider       = databricks.account
  account_id     = var.account_params.account_id
  aws_region     = var.workspace_params.region
  workspace_name = var.workspace_params.workspace_name

  credentials_id           = databricks_mws_credentials.main.credentials_id
  storage_configuration_id = databricks_mws_storage_configurations.main.storage_configuration_id
  network_id               = databricks_mws_networks.main.network_id

  token {
    comment = "Terraform token"
  }
}
