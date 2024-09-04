terraform {
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = ">=1.50.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.58.0"
    }
  }
  backend "s3" {}
}