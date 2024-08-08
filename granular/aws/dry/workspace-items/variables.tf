variable "databricks_token" {
    type = string
    description = "Databricks token with admin access to the corresponding Databricks workspace"
}

variable "workspace_url" {
    type        = string
    description = "Url of the Databricks workspace to deploy resources to"
}

# No need to declare the full variable type here
variable "cluster_params" {
    type = map
}

# No need to declare the full variable type here
variable "workpace_admin_params" {
    type = list
}