variable "kube_prometheus_stack_version" {
  type    = string
  default = "62.3.1"
}

variable "loki_stack_version" {
  type    = string
  default = "2.10.2"
}

variable "pagerduty_service_key" {
  description = "PagerDuty integration key. Pass via a secrets manager / TF_VAR env var — never commit a real value."
  type        = string
  sensitive   = true
}
