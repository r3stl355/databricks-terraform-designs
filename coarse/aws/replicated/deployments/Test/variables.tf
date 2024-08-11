variable "var_file" {
    type        = string
    description = "Name of the JSON file to load containing variable values"
    default     = "variables.json"
}

# The account information should be provided as an invironmental variable. See README.md for an example
variable "account_params" {}