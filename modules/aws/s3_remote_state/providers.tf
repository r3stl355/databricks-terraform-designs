terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.58.0"
      configuration_aliases = [aws.regional]
    }
  }
}