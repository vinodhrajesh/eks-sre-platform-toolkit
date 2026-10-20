# agent-ops

Guardrails for letting coding agents touch infrastructure without putting
production at risk. This repo itself was built mostly with an AI coding
agent (Cursor) — this folder is the pattern that makes that safe to do on
real clusters, not just on toy repos.

## The pattern

1. **Agent proposes, never applies.** An agent can write Terraform, update
   Kubernetes manifests, or draft a runbook — but it never has credentials
   that can run `terraform apply` or `kubectl delete` against production.
2. **Plan review is mandatory and automated.** Every Terraform change goes
   through [`terraform_plan_guardrail.py`](terraform_plan_guardrail.py),
   which parses the plan JSON and hard-blocks any destroy touching a
   protected resource (`module.eks`, `module.rds`, …) unless a named human
   approver is attached.
3. **Dry-run first for anything high-severity.** The self-healing agent
   (`apps/self-healing-agent/`) follows the same rule at runtime: OOMKill
   and node-pressure faults always dry-run and page a human before any
   cordon/drain actually executes.
4. **Scoped, short-lived credentials.** The agent's IAM role (see
   `terraform/modules/eks-cluster/main.tf`) is read-only by default;
   anything mutating requires a short-lived, explicitly-assumed role tied
   to a specific on-call session, never a long-lived key baked into the
   agent's environment.
5. **Everything an agent does is logged where a human already looks.**
   Plan-review results and remediation actions both post to the same Slack
   channel on-call already watches — no separate "agent activity" log that
   nobody checks.

## Files

- [`terraform_plan_guardrail.py`](terraform_plan_guardrail.py) — the plan-review gate described above.
- [`runbook_triage_agent/`](runbook_triage_agent/) — an agent that reads an incoming PagerDuty alert, matches it against the runbooks in `docs/`, and drafts (but does not execute) a triage plan for the on-call engineer to review.
