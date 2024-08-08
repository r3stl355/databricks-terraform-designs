# Terraform template to create resources within a single Databricks Workspace

## Requirements

Following information is required to apply this template

- URL of an existing Databricks Workspace
- Token of a user with Workspace Admin priveledges

*Note:* all the variable values are set either via enfironmental variables (as can be seen in `config.sh`) or a JSON file (e.g. `variables.json` but the name can be configured via the `var_file` variable value). There are no `.tfvars` files.

## Steps

1. Set the environmental variable values in `config.sh` and run it, e.g. `source config.sh` 

2. Set the variables in the `variables.json` file (or whatever other file you set to load in `var_file`).
    
3. Initialize and apply
```
terraform init
terraform plan

#terraform apply
```
