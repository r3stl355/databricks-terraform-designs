
# The account information should be provided as an invironmental variable. See README.md for an example
variable "account_params" {}

# No need to declare the full variable type here, done in `metastore` module
variable "metastore_params" {
	type = map
}