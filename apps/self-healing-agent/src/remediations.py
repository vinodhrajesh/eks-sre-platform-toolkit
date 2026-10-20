"""Remediation actions for each FaultKind.

Every remediation returns an `Action` describing what it did (or would do,
in dry-run mode) so the caller can log it and notify Slack — there is no
silent auto-remediation. High-severity faults always dry-run first; a
human has to flip `CONFIRM_DESTRUCTIVE=true` in the agent's environment
(scoped to a single on-call session) before a real cordon/delete happens.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from detectors import Fault, FaultKind
from kubernetes import client


@dataclass(frozen=True)
class Action:
    description: str
    dry_run: bool
    applied: bool


def remediate(fault: Fault, dry_run: bool) -> Action:
    if fault.kind == FaultKind.CRASH_LOOP:
        return _restart_pod(fault, dry_run)
    if fault.kind == FaultKind.OOM_KILLED:
        return _bump_memory_request_and_alert(fault, dry_run)
    if fault.kind == FaultKind.NODE_PRESSURE:
        return _cordon_node(fault, dry_run)
    raise ValueError(f"No remediation registered for {fault.kind}")


def _confirmed() -> bool:
    return os.environ.get("CONFIRM_DESTRUCTIVE", "false").lower() == "true"


def _restart_pod(fault: Fault, dry_run: bool) -> Action:
    description = f"Delete pod {fault.namespace}/{fault.object_name} to force a clean restart"
    if dry_run or not _confirmed():
        return Action(description=f"[dry-run] {description}", dry_run=True, applied=False)

    v1 = client.CoreV1Api()
    v1.delete_namespaced_pod(name=fault.object_name, namespace=fault.namespace)
    return Action(description=description, dry_run=False, applied=True)


def _bump_memory_request_and_alert(fault: Fault, dry_run: bool) -> Action:
    # OOMKills are flagged high-severity on purpose: we never auto-resize
    # requests/limits in production. The agent's job here is fast detection
    # and a loud page, not a silent fix — see the postmortem for why
    # "quietly patch and move on" made the original incident worse.
    description = (
        f"OOMKilled: {fault.namespace}/{fault.object_name} — "
        "paging on-call instead of auto-patching resource limits"
    )
    return Action(description=description, dry_run=True, applied=False)


def _cordon_node(fault: Fault, dry_run: bool) -> Action:
    description = f"Cordon node {fault.node_name} and drain non-critical pods"
    if dry_run or not _confirmed() or fault.node_name is None:
        return Action(description=f"[dry-run] {description}", dry_run=True, applied=False)

    v1 = client.CoreV1Api()
    body = {"spec": {"unschedulable": True}}
    v1.patch_node(fault.node_name, body)
    return Action(description=description, dry_run=False, applied=True)
