# The account information should be provided as an invironmental variable. See README.md for an example
variable "account_params" {}

variable "workspace_params" {
	description = "Databricks workspace information"
	type = object({
		region 			    = string
		workspace_name  = string
		vpc_cidr		    = string
		metastore_id	  = optional(string)
    metastore_name  = optional(string)
		tags    		    = optional(map(string))
	})
}

variable "account_remote_state_params" {
  description = "Properties of the remote state of the account to lookup values from (not the remote state of this deployment)"
	type = object({
    region      = string
    bucket      = string
    key         = string
    kms_key_id  = string
  })
}
