variable "cluster_name" {
  description = "EKS cluster Karpenter manages nodes for."
  type        = string
}

variable "karpenter_version" {
  description = "Karpenter Helm chart version."
  type        = string
  default     = "1.0.6"
}
