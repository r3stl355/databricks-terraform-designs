resource "databricks_metastore_assignment" "main" {
    provider             = databricks.account
    workspace_id         = databricks_mws_workspaces.main.workspace_id
    metastore_id         = var.workspace_params.metastore_id
    default_catalog_name = "hive_metastore"
}