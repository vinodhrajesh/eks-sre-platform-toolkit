variable "cluster_name" {
  description = "Name of the EKS cluster."
  type        = string
}

variable "cluster_version" {
  description = "Kubernetes version for the control plane (e.g. \"1.31\")."
  type        = string
  default     = "1.31"
}

variable "vpc_id" {
  description = "VPC the cluster's control plane and node groups live in."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for node groups and the control plane ENIs."
  type        = list(string)
}

variable "public_api_access" {
  description = "Whether the EKS API server endpoint is reachable from the public internet. Keep false in production; staging may enable for convenience."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Common resource tags applied across the module."
  type        = map(string)
  default     = {}
}
