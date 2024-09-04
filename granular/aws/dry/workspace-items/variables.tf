# No need to declare the full variable type here
variable "cluster_params" {
    type = map
}

# No need to declare the full variable type here
variable "workpace_admin_params" {
    type = list
}

variable "workspace_remote_state_params" {
  description = "Properties of the remote state of the workspace to lookup values from"
	type = object({
    region      = string
    bucket      = string
    key         = string
    kms_key_id  = string
  })
}