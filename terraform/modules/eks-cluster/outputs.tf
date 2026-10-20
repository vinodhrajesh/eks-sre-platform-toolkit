output "cluster_name" {
  value = module.eks.cluster_name
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "oidc_provider_arn" {
  value = module.eks.oidc_provider_arn
}

output "self_healing_agent_role_arn" {
  value = module.irsa_self_healing_agent.iam_role_arn
}
