# Hydrator - bespoke application tool for a Terragrunt project

We developed this tool specifically for this project to show an alternative way to deploy DRY Terraform projects without using additional 3rd party tools. Furthermore, we built it in such a way that it uses the same configuration as [Terragrunt](https://terragrunt.gruntwork.io/docs/getting-started/install/) which means that you can use either Terragrunt or this tool at any stage without any modifications so long as:
- you use Terragrunt features that are supported by this tool (and you can easily add support for more)
- if you want to use either tool for the same deployment then you make use of a remote state (e.g. S3 backend as shown here)

For example, you could `plan` and `apply` using this tool but can perform subsequent `apply` or `destroy` using Terragrund.

All the DRY projects in the repo can be executed by this tool (or Terragrunt of course).

## Requirements

- The smae requirements as defined in the main [README](../../../../README.md), except for Terragrunt (you don't need that one)
- Python (tested with at least Python 3.8)

## Quick start

Here are complete step-by-step instructions to deploy the metastore, the workspace and some workspace items on AWS

1. Configure a remote S3 backend. You need to use a remote backend if you want to run all the steps with any modifications (only few minor modifications to templates are required to run with local state, no changes to the `hydrator.py`). Remote state is also a requirement if you want to use both Terragrunt and this tool in the same deployment. To help with setting up the backend AWS components we provided a Terraform configuration in `_state` folder. It will create an S3 bucket for state, a KMS key for bucket encryption and a DynamoDB table for locking.

2. Set all the variable values in the following files:
- `granular/aws/dry/_config/Prod/backend.hcl` - contains remote state backend information
- `granular/aws/dry/_config/Prod/account/variables.json`
- `granular/aws/dry/_config/Prod/workspaces/ws-1/workspace/variables.json`
- `granular/aws/dry/_config/Prod/workspaces/ws-1/workspace-items/variables.json` (ignore the `workspace_url` at this point, will be defined later)

3. Set the environmental variables
Specify `TF_VAR_account_params` values. To help with that we provided couple of files, for Linux and Windows (`config.sh` and `config.bat`), just set the values and apply the configuration (e.g.`source config.sh`)

4. Create the account resources (these commands are for Linux, in Windows change `/` in paths to `\`)
```
cd granular/aws/dry/_config/Prod/account
python ../../../hydrator/hydrator.py plan
python ../../../hydrator/hydrator.py apply
```

5. Create the workspace
```
cd granular/aws/dry/_config/Prod/workspaces/ws-1/workspace
python ../../../../../hydrator/hydrator.py plan
python ../../../../../hydrator/hydrator.py apply
```

6. Create the workspace items
```
cd granular/aws/dry/_config/Prod/workspaces/ws-1/workspace-items
python ../../../../../hydrator/hydrator.py plan
python ../../../../../hydrator/hydrator.py apply
```

7. Clean up (you can also run `terragrunt destroy` in each folder to destroy the resources created by `Hydrator`)
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