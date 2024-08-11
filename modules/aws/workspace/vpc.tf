module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "3.2.0"

  name = "${var.workspace_params.workspace_name}-vpc"
  cidr = var.workspace_params.vpc_cidr
  azs  = data.aws_availability_zones.available.names
  tags = var.workspace_params.tags

  enable_dns_hostnames = true
  enable_nat_gateway   = true
  single_nat_gateway   = true
  create_igw           = true

  public_subnets = [cidrsubnet(var.workspace_params.vpc_cidr, 2, 0)]
  private_subnets = [cidrsubnet(var.workspace_params.vpc_cidr, 2, 1), cidrsubnet(var.workspace_params.vpc_cidr, 2, 2)] // Need at least 2 for this module

  manage_default_security_group = true
  default_security_group_name   = "${var.workspace_params.workspace_name}-sg"

  default_security_group_egress = [{
    cidr_blocks = "0.0.0.0/0"
  }]

  default_security_group_ingress = [{
    description = "Allow all internal TCP and UDP"
    cidr_blocks = "0.0.0.0/0"
    self        = true
  }]

  providers = {
    aws = aws.regional
  }
}