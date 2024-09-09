output "kms_key_id" {
	value = var.s3_remote_state_params.add_kms_key ? aws_kms_key.state[0].id : null
}