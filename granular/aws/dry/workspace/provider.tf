terraform {
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = ">=1.16.0"
    }

    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.58.0"
    }
  }
}

provider "aws" {
  region = var.workspace_params.region
}

provider "databricks" {
  alias         = "account"
  host          = local.account_params.account_url
  account_id    = local.account_params.account_id
  client_id     = local.account_params.sp_client_id
  client_secret = local.account_params.sp_client_secret
}