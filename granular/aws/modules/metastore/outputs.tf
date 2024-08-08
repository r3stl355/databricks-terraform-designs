
output "metastores" {
	value = zipmap(values(var.metastore_params)[*].name, values(databricks_metastore.metastore)[*].id)
}