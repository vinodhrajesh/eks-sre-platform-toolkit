variable "repository_names" {
  description = "ECR repositories to apply the lifecycle policy to."
  type        = list(string)
}

variable "max_tagged_images" {
  description = "Max number of CI/staging-tagged images to retain per repository before the oldest are expired."
  type        = number
  default     = 20
}
