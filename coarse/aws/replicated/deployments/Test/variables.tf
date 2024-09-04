variable "var_file_prefix" {
    type        = string
    description = "Prefix of the default `variables.json` file name containing variable values, e.g. `test.` to load values from `test.variables.json`"
    default     = ""
}

# The account information should be provided as an invironmental variable. See README.md for an example
variable "account_params" {}