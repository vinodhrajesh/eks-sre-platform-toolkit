# Architecture

```
                 Internet
                    │
                 Akamai (edge/WAF)
                    │
               CloudFront (CDN)
                    │
              ALB/NLB (TLS termination)
                    │
   ┌────────────────┴─────────────────┐
   │              EKS cluster          │
   │                                   │
   │  namespace: platform              │
   │   ├─ platform-api (PriorityClass: platform-critical)
   │   ├─ platform-worker (KEDA-scaled on SQS queue depth)
   │   └─ self-healing-agent (watches Events cluster-wide)
   │                                   │
   │  namespace: monitoring            │
   │   ├─ kube-prometheus-stack (metrics + alerting)
   │   └─ loki + promtail (logs)       │
   │                                   │
   │  node groups                      │
   │   ├─ system (static, 2-4 nodes, cluster-critical add-ons)
   │   └─ Karpenter-managed (elastic, Spot + on-demand)
   └───────────────────────────────────┘
                    │
            RDS PostgreSQL (primary + read replica)
```

## Design decisions, and the incidents behind them

**Why a static `system` node group instead of 100% Karpenter?** Cluster-
critical add-ons (CoreDNS, the self-healing-agent itself) need to survive
even if Karpenter's own capacity provisioning stalls. Mixing "the thing
that heals the cluster" into the elastic pool it depends on is a single
point of failure.

**Why `PodDisruptionBudget`s on every stateful workload?** See
[`docs/incident-postmortems/`](incident-postmortems/) — a node-consolidation
event without PDBs left workloads stuck mid-eviction. PDBs plus a tuned
Karpenter `consolidateAfter` fixed it without giving up the cost savings
from aggressive bin-packing.

**Why does the observability stack alert on QoS/memory headroom instead
of just "pod restarted"?** A restart count alert fires after the damage is
done. A memory-headroom alert (`PodMemoryNearLimit` in
`terraform/modules/observability-stack/main.tf`) fires before the OOMKill,
giving on-call a chance to intervene first.

**Why a read replica instead of just a bigger primary?** Read-heavy
reporting queries and transactional writes were competing for the same
I/O and connection pool. Separating them (`docs/incident-postmortems/…rds…`)
fixes the contention permanently instead of buying a few months with a
bigger instance.

**Why does `agent-ops/` exist at all?** Because this repo — Terraform,
Kubernetes manifests, and the self-healing agent's code — was written
mostly by an AI coding agent. The guardrail in
[`terraform_plan_guardrail.py`](../agent-ops/terraform_plan_guardrail.py)
is what makes letting an agent touch infrastructure code something a
reviewer can actually trust.
