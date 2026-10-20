#
# EKS cluster module.
#
# Boring on purpose: a small, always-on "system" node group for cluster-
# critical add-ons (CoreDNS, CSI drivers, the self-healing-agent), with all
# elastic application capacity delegated to Karpenter (see ../karpenter).
# This split is what let us isolate heavy AI/OCR workloads onto their own
# node pools without starving platform components during a scale-up event.
#

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  vpc_id     = var.vpc_id
  subnet_ids = var.private_subnet_ids

  cluster_endpoint_public_access       = var.public_api_access
  cluster_endpoint_private_access      = true
  enable_cluster_creator_admin_permissions = true

  eks_managed_node_groups = {
    system = {
      instance_types = ["m6i.large"]
      min_size       = 2
      max_size       = 4
      desired_size   = 2
      labels = {
        role = "system"
      }
      # System node group is intentionally never autoscaled by Karpenter —
      # cluster-critical add-ons must survive even if Karpenter itself is down.
      taints = []
    }
  }

  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }

  tags = merge(var.tags, {
    "karpenter.sh/discovery" = var.cluster_name
  })
}

# IRSA role consumed by Karpenter and the self-healing agent to talk to the
# AWS API without long-lived static credentials.
module "irsa_self_healing_agent" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name = "${var.cluster_name}-self-healing-agent"

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["platform:self-healing-agent"]
    }
  }

  role_policy_arns = {
    read_only = "arn:aws:iam::aws:policy/ReadOnlyAccess"
  }

  tags = var.tags
}
