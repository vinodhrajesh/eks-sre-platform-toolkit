"""Posts every detected fault and the action taken to a Slack ChatOps
channel. This is the audit trail: every remediation shows up here whether
it actually ran or stayed in dry-run.
"""

from __future__ import annotations

import json
import os
import urllib.request

from detectors import Fault
from remediations import Action

_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")


def notify(fault: Fault, action: Action) -> None:
    if not _WEBHOOK_URL:
        print(f"[notify-skip, no SLACK_WEBHOOK_URL] {fault.kind.value} -> {action.description}")
        return

    status = "applied" if action.applied else "dry-run only"
    text = (
        f":rotating_light: *{fault.kind.value}* in `{fault.namespace}/{fault.object_name}` "
        f"(severity: {fault.severity})\n{action.description}\n_status: {status}_"
    )

    req = urllib.request.Request(
        _WEBHOOK_URL,
        data=json.dumps({"text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception as exc:  # noqa: BLE001 — never let a notify failure crash the agent
        print(f"[notify-error] failed to post to Slack: {exc}")
