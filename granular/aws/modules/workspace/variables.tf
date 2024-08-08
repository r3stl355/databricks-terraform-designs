variable "workspace_params" {
	description = "Databricks workspace information"
	type = object({
		region 			= string
		workspace_name  = string
		vpc_cidr		= string
		metastore_id	= string
		tags    	= optional(map(string))
	})
}

variable "account_params" {
    description = "Databricks account information"
    type = object({
        account_url         = string
        account_id          = string
        sp_client_id        = string
        sp_client_secret    = string
    })
}