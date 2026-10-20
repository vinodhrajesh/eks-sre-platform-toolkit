# runbook-triage-agent

Reads an incoming PagerDuty alert payload, matches it against the runbooks
in [`docs/`](../../docs/), and drafts a triage plan — likely root causes to
check first, the exact commands to run, and which runbook to follow. The
on-call engineer reviews and runs the plan; the agent never executes
anything against the cluster itself.

This exists because the fastest part of the two incidents in
[`docs/incident-postmortems/`](../../docs/incident-postmortems/) was
finding the right runbook once the alert fired — the slow part was getting
from "something's wrong" to "I know which runbook applies." This closes
that gap without giving an agent any write access to production.
