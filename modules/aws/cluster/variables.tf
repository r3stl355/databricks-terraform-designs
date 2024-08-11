variable "cluster_params" {
	description = "Databricks cluster information"
	type = map(object({
		cluster_name    		= string
		security_mode			= string
		auto_terminate_minutes	= number

		user_name				= optional(string)
		tags    				= optional(map(string))
	}))
}