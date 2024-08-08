resource "databricks_metastore" "metastore" {
  for_each      = var.metastore_params

  region        = each.value.region
  name          = each.value.name
  owner         = each.value.owner
  force_destroy = false
}