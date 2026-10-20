# Runbook: Node disk/memory pressure

**Trigger:** `NodeDiskPressure` / `NodeHasMemoryPressure` alert, or a
cluster-wide spike in pod evictions.

## 1. Confirm scope

```bash
kubectl get nodes -o wide
kubectl describe node <node> | grep -A10 Conditions
```

## 2. Check for a recent Karpenter consolidation event

```bash
kubectl get events -A --field-selector reason=Disrupted --sort-by=.lastTimestamp
```

If multiple nodes terminated close together, check whether every affected
workload has a `PodDisruptionBudget`
([`kubernetes/policies/pod-disruption-budgets.yaml`](../../kubernetes/policies/pod-disruption-budgets.yaml)).
Missing PDBs are the most common cause of "stuck Terminating" pods during
consolidation — see the Karpenter module comments in
[`terraform/modules/karpenter/main.tf`](../../terraform/modules/karpenter/main.tf)
for the `consolidateAfter` tuning this came from.

## 3. Stabilize

```bash
kubectl cordon <node>          # stop new pods landing here
kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
```

The self-healing agent dry-runs this exact sequence automatically for
`NodeHasMemoryPressure`/`NodeHasDiskPressure` events and pages on-call
before actually cordoning — check Slack before doing this manually to
avoid double-draining.

## 4. Fix

- If caused by over-aggressive consolidation: increase
  `disruption.consolidateAfter` in the Karpenter `NodePool`.
- If caused by genuinely under-provisioned capacity: check the `NodePool`
  `limits.cpu` ceiling isn't being hit.

## 5. Postmortem trigger

If this caused any customer-visible impact, follow the postmortem format
in [`docs/incident-postmortems/`](../incident-postmortems/).
