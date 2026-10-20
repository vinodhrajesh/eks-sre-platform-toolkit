# Runbook: OOMKilled / CrashLoopBackOff

**Trigger:** `PodMemoryNearLimit` alert, or a `BackOff`/`OOMKilling` event
surfaced by the self-healing agent in Slack.

## 1. Confirm scope

```bash
kubectl get pods -n platform --field-selector=status.phase!=Running
kubectl top pod -n platform --sort-by=memory
```

Is this one pod, one Deployment, or spread across multiple unrelated
workloads? Spread-out symptoms usually mean node-level pressure, not an
app-level leak — jump to the [node-pressure runbook](node-pressure.md).

## 2. Check the self-healing agent's action log in Slack

The agent dry-runs and posts before anyone intervenes manually — check
whether it already restarted the pod and whether it recurred.

## 3. Find the actual cause

```bash
kubectl describe pod <pod> -n platform | grep -A5 "Last State"
kubectl logs <pod> -n platform --previous
```

Common causes, in order of frequency seen so far:

1. Missing or too-low `resources.limits.memory` — check against
   [`kubernetes/base/limit-range.yaml`](../../kubernetes/base/limit-range.yaml)
   to confirm the default actually applied.
2. A genuine memory leak in a long-running worker.
3. A sudden increase in request/batch size (e.g. a bulk job) that the
   existing limit never anticipated.

## 4. Fix

- For a misconfigured limit: patch the Deployment's `resources` block,
  roll out, confirm `PodMemoryNearLimit` clears.
- For a leak: roll back to the last known-good image while a fix ships.

## 5. Postmortem trigger

If this caused any customer-visible impact, write a postmortem using the
template in
[`docs/incident-postmortems/2026-oomkill-cascade-self-healing-agent.md`](../incident-postmortems/2026-oomkill-cascade-self-healing-agent.md).
