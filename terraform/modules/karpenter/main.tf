#
# Karpenter autoscaling module.
#
# Replaces static ASG-based node groups for all elastic application
# capacity. The NodePool below is deliberately conservative on
# consolidation — see docs/incident-postmortems for why: an earlier,
# more aggressive disruption budget caused multiple nodes to terminate
# simultaneously during a Spot-interruption spike with no PodDisruptionBudgets
# in place, leaving stateful workloads stuck mid-eviction.
#

resource "helm_release" "karpenter" {
  name       = "karpenter"
  namespace  = "kube-system"
  repository = "oci://public.ecr.aws/karpenter"
  chart      = "karpenter"
  version    = var.karpenter_version

  set {
    name  = "settings.clusterName"
    value = var.cluster_name
  }

  set {
    name  = "settings.interruptionQueue"
    value = aws_sqs_queue.karpenter_interruption.name
  }
}

# Spot interruption notices land here so Karpenter can cordon + drain
# gracefully instead of letting the node vanish mid-request.
resource "aws_sqs_queue" "karpenter_interruption" {
  name                      = "${var.cluster_name}-karpenter-interruption"
  message_retention_seconds = 300
}

resource "kubectl_manifest" "node_pool_default" {
  yaml_body = <<-YAML
    apiVersion: karpenter.sh/v1
    kind: NodePool
    metadata:
      name: default
    spec:
      template:
        spec:
          requirements:
            - key: karpenter.sh/capacity-type
              operator: In
              values: ["spot", "on-demand"]
            - key: kubernetes.io/arch
              operator: In
              values: ["amd64"]
          nodeClassRef:
            group: karpenter.k8s.aws
            kind: EC2NodeClass
            name: default
      disruption:
        consolidationPolicy: WhenEmptyOrUnderutilized
        # Longer-than-default consolidateAfter gives PodDisruptionBudgets time
        # to be honored before Karpenter reclaims a node. Tuned up after the
        # incident in docs/incident-postmortems/ — see that writeup for the
        # before/after numbers.
        consolidateAfter: 5m
      limits:
        cpu: "1000"
  YAML
}
