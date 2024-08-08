data "databricks_group" "admins" {
  provider      = databricks.workspace
  display_name  = "admins"
}

resource "databricks_user" "user" {
  for_each    = {for v in var.workpace_admin_params: v => v}
  provider    = databricks.workspace
  user_name   = each.value
}

resource "databricks_group_member" "admin_user" {
  for_each  = {for i, user in databricks_user.user: i => user}
  provider  = databricks.workspace
  group_id  = data.databricks_group.admins.id
  member_id = each.value.id
}