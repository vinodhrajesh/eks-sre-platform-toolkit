# Postmortem: OOMKill cascade during a traffic spike

- **Status:** Resolved
- **Severity:** SEV-2 — partial outage, ~20 minutes
- **Author:** Vinodh Rajesh
- **Postmortem type:** Blameless — this document assigns causes, not blame

## Summary

A sudden traffic spike triggered cascading `OOMKilled` events across a
subset of EKS workloads that lacked standardized memory requests/limits.
As those pods were evicted and rescheduled, the extra churn pushed
neighboring pods on the same nodes into memory pressure too, causing a
~20-minute partial outage affecting a subset of API traffic.

## Impact

- A subset of API requests returned 5xx or timed out for ~20 minutes.
- Several background workers were evicted and restarted mid-job, requiring
  manual re-queueing of a small number of jobs afterward.
- No data loss. No customer-facing security impact.

## Timeline (all times approximate, IST)

- **T+0:00** — Traffic spike begins (feature launch drove higher-than-forecast load).
- **T+0:03** — First `OOMKilled` events appear on a handful of pods without memory limits set.
- **T+0:06** — PagerDuty pages on-call on an elevated 5xx-rate alert (symptom-level, not root cause).
- **T+0:09** — On-call engineer (me) opens Grafana; memory-saturation panel for the affected
  namespace shows several pods pinned at 100% of node-allocatable memory with no limit configured.
- **T+0:14** — Root cause identified: a recent deployment omitted resource `limits`, letting the pod
  consume unbounded memory and starve neighbors on the same node (BestEffort/Burstable QoS collision).
- **T+0:17** — Mitigation: patched the affected Deployments with explicit requests/limits and
  `PriorityClass`, restarted the affected pods cleanly.
- **T+0:20** — Error rate and latency return to baseline. Incident resolved.

## Root cause

The affected Deployments had no `resources.requests` / `resources.limits`
set, which defaults them to `BestEffort` QoS. Under memory pressure, the
kubelet evicts `BestEffort` pods first — but because several such pods
landed on the same nodes, the eviction and OOM-kill activity cascaded
faster than the scheduler could rebalance, producing a visible outage
instead of a quiet, isolated restart.

There was no cluster-wide guardrail (quota, `LimitRange`, or alert)
to catch a deployment missing resource limits before it reached
production.

## What changed afterward

1. **Standardized resource requests/limits and QoS classes** across every
   workload in the `platform` namespace — see
   [`kubernetes/base/limit-range.yaml`](../../kubernetes/base/limit-range.yaml),
   which now gives any container without explicit values a sane default
   instead of silently falling into `BestEffort`.
2. **Added `PriorityClass`es** ([`kubernetes/base/priority-classes.yaml`](../../kubernetes/base/priority-classes.yaml))
   so request-path workloads are the last to be preempted under node pressure,
   not the first.
3. **Added a leading-indicator alert**, `PodMemoryNearLimit`
   (see [`terraform/modules/observability-stack/main.tf`](../../terraform/modules/observability-stack/main.tf)),
   that fires at 85% of a pod's memory limit — before the OOMKill, not after.
4. **Built the self-healing EKS agent** ([`apps/self-healing-agent/`](../../apps/self-healing-agent/)),
   which now watches for `CrashLoopBackOff`, `OOMKilled`, and node-pressure
   events cluster-wide, pages on-call immediately with full context, and
   safely remediates the low-risk cases (clean pod restarts) automatically
   while leaving anything destructive to dry-run-plus-human-confirmation.
   This cut MTTR for this entire class of incident from ~20 minutes to
   under 2.

## Action items

| Action | Owner | Status |
| --- | --- | --- |
| Add `LimitRange` + default QoS to all namespaces | Vinodh | Done |
| Add `PodMemoryNearLimit` leading-indicator alert | Vinodh | Done |
| Build self-healing-agent for automated detection/remediation | Vinodh | Done |
| Add a CI check that rejects manifests with no resource limits | Vinodh | Follow-up |
