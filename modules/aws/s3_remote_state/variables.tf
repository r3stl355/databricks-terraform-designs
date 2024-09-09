variable "s3_remote_state_params" {
  description = "Resources to support S3 based remote state"
	type = object({
		bucket_name	        = string
    add_kms_key         = bool
    dynamodb_table_name = optional(string)
		tags    	          = optional(map(string))
	})
}