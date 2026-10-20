terraform {
  required_version = ">= 1.6"
}

provider "aws" {
  region = var.aws_region
}

module "eks_cluster" {
  source = "../../modules/eks-cluster"

  cluster_name       = "platform-staging"
  cluster_version    = "1.31"
  vpc_id             = var.vpc_id
  private_subnet_ids = var.private_subnet_ids
  public_api_access  = true # convenience for staging only — never enable in production

  tags = {
    environment = "staging"
    managed_by  = "terraform"
  }
}

module "karpenter" {
  source = "../../modules/karpenter"

  cluster_name = module.eks_cluster.cluster_name
}

module "ecr_lifecycle" {
  source = "../../modules/ecr-lifecycle"

  repository_names  = var.ecr_repository_names
  max_tagged_images = 10
}

module "observability" {
  source = "../../modules/observability-stack"

  pagerduty_service_key = var.pagerduty_service_key
}
