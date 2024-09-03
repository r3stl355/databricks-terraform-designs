provider "databricks" {
  alias         = "account"
  host          = local.account_params.account_url
  account_id    = local.account_params.account_id
  client_id     = local.account_params.sp_client_id
  client_secret = local.account_params.sp_client_secret
}