variable "s3_remote_state_params" {
  description = "Resources to support S3 based remote state"
	type = object({
		bucket_name	        = string
    dynamodb_table_name = string
		tags    	          = optional(map(string))
	})
}