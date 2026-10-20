# Postmortem: Primary RDS saturation from reporting-style queries

- **Status:** Resolved
- **Severity:** SEV-2 — degraded API latency and intermittent timeouts, ~35 minutes
- **Author:** Vinodh Rajesh
- **Postmortem type:** Blameless — this document assigns causes, not blame

## Summary

A newly shipped feature issued reporting-style, read-heavy queries
directly against the primary PostgreSQL RDS instance. Under moderate
production load, these queries saturated primary CPU and the connection
pool, causing API timeouts across multiple EKS services whose requests
depend on the same database.

## Impact

- Elevated p99 latency and intermittent 5xx responses across several
  API services for ~35 minutes.
- No data loss or data corruption. No customer-facing security impact.

## Timeline (all times approximate, IST)

- **T+0:00** — New feature's background job begins running a reporting
  query on a schedule, hitting the primary RDS instance directly.
- **T+0:05** — CloudWatch RDS CPU utilization alarm fires at ~95% sustained.
- **T+0:07** — On-call engineer (me) correlates the CPU spike with rising
  API latency across unrelated services sharing the same database.
- **T+0:12** — `pg_stat_activity` and RDS Performance Insights show a
  small number of long-running, unindexed queries holding connections and
  competing with transactional traffic for I/O.
- **T+0:18** — Mitigation: paused the offending scheduled job and killed
  the long-running queries to free connections immediately.
- **T+0:25** — Added missing indexes for the reporting query's filter
  columns and re-enabled the job on a lower-impact schedule.
- **T+0:35** — Latency and error rate return to baseline. Incident resolved.

## Root cause

The new feature's reporting queries were unindexed on their primary
filter columns, forcing sequential scans against a large table, and ran
on the same RDS instance and connection pool as transactional
request-path traffic. There was no separation between
read-heavy/analytical workloads and the transactional primary, so a
single inefficient query pattern could degrade every service sharing
that database.

## What changed afterward

1. **Added the missing indexes** for the reporting query's filter columns,
   removing the immediate performance cliff.
2. **Provisioned a dedicated RDS read-replica** and an **AWS DMS task** to
   permanently offload heavy read/reporting queries from the primary,
   so this class of workload can no longer compete with transactional
   traffic for the same resources.
3. **Documented the separation as a standing rule**: any new
   reporting/analytics query must target the read replica, enforced at
   code-review time via a connection-string convention
   (`*_READ_REPLICA_URL` vs `*_PRIMARY_URL`).
4. **Added a CloudWatch alarm on replica lag**, so if the replica ever
   falls meaningfully behind the primary, on-call is paged before stale
   reporting data becomes a second-order incident.

## Action items

| Action | Owner | Status |
| --- | --- | --- |
| Add missing indexes on reporting query filter columns | Vinodh | Done |
| Provision RDS read-replica + AWS DMS offload task | Vinodh | Done |
| Document primary-vs-replica connection convention | Vinodh | Done |
| Add replica-lag alarm | Vinodh | Done |
