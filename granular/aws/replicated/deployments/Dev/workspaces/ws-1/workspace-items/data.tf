data "terraform_remote_state" "workspace" {
  backend = "local"
  config = {
    path = "../workspace/terraform.tfstate"
  }
}