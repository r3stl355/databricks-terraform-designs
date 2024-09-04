data "terraform_remote_state" "account" {
  backend = "local"
  config  = {
    path = "../../../account/terraform.tfstate"
  }
}