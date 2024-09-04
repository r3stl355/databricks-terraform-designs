terraform {
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = ">=1.50.0"
    }
  }
  backend "s3" {}
}