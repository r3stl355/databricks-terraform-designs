terraform {
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = ">=1.51.0"
    }
  }
  backend "s3" {}
}