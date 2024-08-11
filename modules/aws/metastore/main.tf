resource "databricks_metastore" "metastore" {
  for_each      = var.metastore_params
  
  provider       = databricks.account
  region        = each.value.region
  name          = each.value.name
  owner         = each.value.owner
  force_destroy = true
}