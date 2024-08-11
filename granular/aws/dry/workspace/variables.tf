# The account information should be provided as an invironmental variable. See README.md for an example
variable "account_params" {}

variable "workspace_params" {
	description = "Databricks workspace information"
	type = object({
		region 			= string
		workspace_name  = string
		vpc_cidr		= string
		metastore_id	= string
		tags    		= optional(map(string))
	})
}

