variable "aws_region" {
  type    = string
  default = "ap-south-1"
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "ecr_repository_names" {
  type = list(string)
}

variable "pagerduty_service_key" {
  type      = string
  sensitive = true
}
