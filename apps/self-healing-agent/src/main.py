"""Self-healing EKS agent entrypoint.

Watches the cluster's Event stream for CrashLoopBackOff, OOMKilled, and
node-pressure signals, classifies each one, runs the matching remediation
(dry-run for anything high-severity until a human confirms), and posts a
summary of every action to Slack. Originally built in response to a real
production incident — see
docs/incident-postmortems/2026-xx-oomkill-cascade-self-healing-agent.md —
and now runs continuously, org-wide, as a ChatOps-visible safety net.
"""

from __future__ import annotations

import logging

from detectors import classify_fault
from kubernetes import client, config, watch
from notifier_slack import notify
from remediations import remediate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("self-healing-agent")


def run() -> None:
    try:
        config.load_incluster_config()
    except config.ConfigException:
        # Local/dev fallback so this runs against `kind`/minikube too.
        config.load_kube_config()

    v1 = client.CoreV1Api()
    w = watch.Watch()

    log.info("self-healing-agent started — watching for faults across all namespaces")

    for raw_event in w.stream(v1.list_event_for_all_namespaces):
        event = raw_event["raw_object"]
        fault = classify_fault(event)
        if fault is None:
            continue

        log.info("fault detected: %s in %s/%s", fault.kind.value, fault.namespace, fault.object_name)

        action = remediate(fault, dry_run=fault.severity == "high")
        notify(fault, action)


if __name__ == "__main__":
    run()
