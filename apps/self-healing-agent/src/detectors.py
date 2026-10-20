"""Classifies raw Kubernetes Event objects into actionable Fault records.

Kept deliberately simple and rule-based rather than ML-based: on-call
engineers need to be able to read this file in under a minute and know
exactly why the agent took an action. "AI-based" in this project means an
AI coding agent built and maintains it, under human review — not that the
runtime decision logic is a black box.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FaultKind(str, Enum):
    CRASH_LOOP = "crash_loop_backoff"
    OOM_KILLED = "oom_killed"
    NODE_PRESSURE = "node_pressure"


@dataclass(frozen=True)
class Fault:
    kind: FaultKind
    namespace: str
    object_name: str
    node_name: str | None
    reason: str
    severity: str  # "low" | "medium" | "high"


# Kubernetes Event .reason values we care about, mapped to a FaultKind and
# how risky it is to auto-remediate. "high" severity faults always run in
# dry-run mode first and require a human to confirm before anything
# destructive happens (see agent-ops/terraform_plan_guardrail.py for the
# equivalent concept applied to infrastructure changes).
_REASON_MAP: dict[str, tuple[FaultKind, str]] = {
    "BackOff": (FaultKind.CRASH_LOOP, "medium"),
    "OOMKilling": (FaultKind.OOM_KILLED, "high"),
    "NodeHasDiskPressure": (FaultKind.NODE_PRESSURE, "high"),
    "NodeHasMemoryPressure": (FaultKind.NODE_PRESSURE, "high"),
}


def classify_fault(event: dict) -> Fault | None:
    """Map a Kubernetes Event dict (as returned by the watch stream) to a
    Fault, or None if the event isn't one we act on.
    """
    reason = event.get("reason", "")
    mapping = _REASON_MAP.get(reason)
    if mapping is None:
        return None

    kind, severity = mapping
    involved = event.get("involvedObject", {})

    return Fault(
        kind=kind,
        namespace=event.get("metadata", {}).get("namespace", "unknown"),
        object_name=involved.get("name", "unknown"),
        node_name=event.get("source", {}).get("host"),
        reason=reason,
        severity=severity,
    )
