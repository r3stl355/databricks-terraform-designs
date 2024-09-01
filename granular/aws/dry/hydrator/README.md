# Hydrator - bespoke application tool for a DRY Terraform project

We developed this tool specifically for this project to show an alternative way to deploy DRY Terraform projects without using additional 3rd party tools. Furthermore, we built it in such a way that it uses the same configuration as [Terragrunt](https://terragrunt.gruntwork.io/docs/getting-started/install/) which means that you can run a Terragrunt project using this tool without any modifications (so long as it uses only Terragrunt features that we used in this project, and you can easily add support for more). 

All the DRY designs in the repo can be executed by this tool (or Terragrunt of course).

## Requirements

- Requirements defined in the main [README](../../../../README.md) except for Terragrunt (you don't need that one)
- Python

### Quick start

Here is a full

1. Set all the variable values in the following files:
- `granular/aws/dry/_config/Prod/account/variables.json`
- `granular/aws/dry/_config/Prod/workspaces/ws-1/workspace/variables.json`
- `granular/aws/dry/_config/Prod/workspaces/ws-1/workspace-items/variables.json` (ignore the `workspace_url` at this point, will be defined later)

2. Set the environmental variables
- Specify `TF_VAR_account_params` values
- Apply the configuration
```
source config.sh
```

3. Create the account resources
```
cd granular/aws/dry/_config/Prod/account
python ../../../hydrator/hydrator.py plan
python ../../../hydrator/hydrator.py apply
```

4. Create the workspace
```
cd granular/aws/dry/_config/Prod/workspaces/ws-1/workspace
python ../../../../../hydrator/hydrator.py plan
python ../../../../../hydrator/hydrator.py apply
```

***TODO:*** remove this after implementing `terraform_remote_state` lookup
4.2 Apply additional config 
- Take a note of the `workspace_url` output and set the value of `worspace_url` property in `granular/aws/dry/_config/Prod/workspaces/ws-1/workspace-items/variables.json`
- Lookup the `databricks_token` in the `_hydrator/terraform.tfstate` file and use it to set the value of `TF_VAR_databricks_token` in the `setup.sh`
- Re-apply the configuration again
```
source config.sh
```

5. Create the workspace items
```
cd granular/aws/dry/_config/Prod/workspaces/ws-1/workspace-items
python ../../../../../hydrator/hydrator.py plan
python ../../../../../hydrator/hydrator.py apply
```

6. Clean up
```
cd granular/aws/dry/_config/Prod/workspaces/ws-1/workspace-items
python ../../../../../hydrator/hydrator.py destroy
```
```
cd granular/aws/dry/_config/Prod/workspaces/ws-1/workspace
python ../../../../../hydrator/hydrator.py destroy
```
```
cd granular/aws/dry/_config/Prod/account
python ../../../hydrator/hydrator.py destroy
```