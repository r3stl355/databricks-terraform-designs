terraform {
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = ">=1.50.0"
    }
  }
}

provider "aws" {
  alias  = "ws_1"
  region = local.workspace_params.ws_1.region
}

provider "aws" {
  alias  = "ws_2"
  region = local.workspace_params.ws_2.region
}

provider "databricks" {
  alias         = "account"
  host          = local.account_params.account_url
  account_id    = local.account_params.account_id
  client_id     = local.account_params.sp_client_id
  client_secret = local.account_params.sp_client_secret
}

provider "databricks" {
  alias         = "ws_1"
  host          = module.ws_1.workspace_url
  token         = module.ws_1.databricks_token
}

provider "databricks" {
  alias         = "ws_2"
  host          = module.ws_2.workspace_url
  token         = module.ws_2.databricks_token
}