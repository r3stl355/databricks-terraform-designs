variable "metastore_params" {
	description = "Unity Catalog metastore information"
	type = map(object({
		region 	= string
		name    = string
		owner	= string
	}))
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