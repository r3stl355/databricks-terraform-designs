data "databricks_spark_version" "latest" {
  provider  = databricks.workspace
}

data "databricks_node_type" "default" {
  provider    = databricks.workspace
  local_disk  = true
}

resource "databricks_cluster" "cluster" {
  provider                = databricks.workspace
  for_each                = var.cluster_params
  cluster_name            = each.value.cluster_name
  data_security_mode      = each.value.security_mode
  single_user_name        = each.value.security_mode == "SINGLE_USER" ? each.value.user_name : null
  spark_version           = data.databricks_spark_version.latest.id  // "13.3.x-scala2.12"
  node_type_id            = data.databricks_node_type.default.id
  autotermination_minutes = each.value.auto_terminate_minutes

  # Creating single-node clusters
  spark_conf = {
    "spark.databricks.cluster.profile" : "singleNode"
    "spark.master" : "local[*]"
  }
  custom_tags = merge(each.value.tags, {"ResourceClass" = "SingleNode"})
}
