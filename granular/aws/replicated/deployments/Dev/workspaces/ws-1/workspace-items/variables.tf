variable "var_file" {
    type        = string
    description = "Name of the JSON file to load containing variable values"
    default     = "variables.json"
}

variable "databricks_token" {
    type        = string
    description = "Databricks token with admin access to the corresponding Databricks workspace"
}