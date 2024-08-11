terraform {
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = ">=1.16.0"
      configuration_aliases = [databricks.account]
    }

    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.58.0"
      configuration_aliases = [aws.regional]
    }
  }
}