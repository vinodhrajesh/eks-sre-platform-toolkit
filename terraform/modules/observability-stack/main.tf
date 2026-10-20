#
# Observability stack module.
#
# kube-prometheus-stack for metrics + alerting, Loki + Promtail for logs.
# Alert rules are written to point at root cause, not symptom — e.g. the
# memory-saturation + QoS-class alerts below are what should have fired
# before the OOMKill cascade described in docs/incident-postmortems/.
#

resource "helm_release" "kube_prometheus_stack" {
  name             = "kube-prometheus-stack"
  namespace        = "monitoring"
  create_namespace = true
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  version          = var.kube_prometheus_stack_version

  values = [
    yamlencode({
      alertmanager = {
        config = {
          receivers = [
            {
              name = "pagerduty-critical"
              pagerduty_configs = [
                { service_key = var.pagerduty_service_key }
              ]
            }
          ]
        }
      }
      additionalPrometheusRulesMap = {
        "sre-platform-rules" = {
          groups = [
            {
              name = "node-and-pod-capacity"
              rules = [
                {
                  alert = "PodMemoryNearLimit"
                  expr  = "container_memory_working_set_bytes / on(pod) kube_pod_container_resource_limits{resource=\"memory\"} > 0.85"
                  for   = "5m"
                  labels = { severity = "warning" }
                  annotations = {
                    summary = "Pod {{ $labels.pod }} is above 85% of its memory limit — OOMKill risk"
                  }
                },
                {
                  alert = "NodeDiskPressure"
                  expr  = "kube_node_status_condition{condition=\"DiskPressure\",status=\"true\"} == 1"
                  for   = "2m"
                  labels = { severity = "critical" }
                  annotations = {
                    summary = "Node {{ $labels.node }} is under disk pressure"
                  }
                }
              ]
            }
          ]
        }
      }
    })
  ]
}

resource "helm_release" "loki" {
  name             = "loki"
  namespace        = "monitoring"
  repository       = "https://grafana.github.io/helm-charts"
  chart            = "loki-stack"
  version          = var.loki_stack_version
  create_namespace = false

  set {
    name  = "promtail.enabled"
    value = "true"
  }
}
