terraform {
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = ">=1.16.0"
    }
  }
}

provider "databricks" {
  alias         = "workspace"
  host          = var.workspace_url
  token         = var.databricks_token
}