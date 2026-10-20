#!/usr/bin/env python3
"""Matches an incoming alert to a runbook and drafts (never executes) a
triage plan for the on-call engineer.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TriagePlan:
    alert_name: str
    likely_causes: list[str]
    first_commands: list[str]
    runbook_path: str


# Keyword -> runbook mapping. Deliberately simple keyword matching rather
# than an LLM call: triage needs to be fast, deterministic, and auditable —
# an on-call engineer at 2am should be able to see exactly why a runbook
# was suggested.
_RUNBOOK_MAP: dict[str, TriagePlan] = {
    "PodMemoryNearLimit": TriagePlan(
        alert_name="PodMemoryNearLimit",
        likely_causes=[
            "Missing or too-low memory limit on a Deployment/StatefulSet",
            "Memory leak in a long-running worker process",
            "Traffic spike pushing a BestEffort/Burstable pod toward its limit",
        ],
        first_commands=[
            "kubectl top pod -n platform --sort-by=memory",
            "kubectl describe pod <pod> -n platform | grep -A5 'Last State'",
        ],
        runbook_path="docs/runbooks/oomkill-crashloop.md",
    ),
    "NodeDiskPressure": TriagePlan(
        alert_name="NodeDiskPressure",
        likely_causes=[
            "Karpenter consolidation evicted multiple pods onto one node",
            "A node is stuck mid-drain with pods not honoring PodDisruptionBudget",
        ],
        first_commands=[
            "kubectl get nodes -o wide",
            "kubectl get pdb -A",
        ],
        runbook_path="docs/runbooks/node-pressure.md",
    ),
}


def triage(alert_name: str) -> TriagePlan | None:
    return _RUNBOOK_MAP.get(alert_name)


if __name__ == "__main__":
    import sys

    plan = triage(sys.argv[1] if len(sys.argv) > 1 else "")
    if plan is None:
        print("No matching runbook — escalate to on-call lead for manual triage.")
    else:
        print(f"Suggested runbook: {plan.runbook_path}")
        print("Likely causes:")
        for cause in plan.likely_causes:
            print(f"  - {cause}")
        print("First commands to run:")
        for cmd in plan.first_commands:
            print(f"  $ {cmd}")
