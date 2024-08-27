variable "metastore_params" {
	description = "Unity Catalog metastore information"
	type = map(object({
		region 	= string
		name    = string
		owner	= string
	}))
}