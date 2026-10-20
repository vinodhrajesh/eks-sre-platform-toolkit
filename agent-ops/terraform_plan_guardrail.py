#!/usr/bin/env python3
"""Terraform plan-review guardrail for agent-driven infrastructure changes.

Usage:
    terraform plan -out=plan.out
    terraform show -json plan.out > plan.json
    python terraform_plan_guardrail.py plan.json --approver "vinodh"

Wraps `terraform plan` so an AI coding agent can propose infrastructure
changes without ever touching `apply` directly: it blocks any destroy that
touches a protected resource unless a named human approver is passed in,
and it always prints a human-readable summary so a reviewer doesn't have
to read raw plan JSON.
"""

from __future__ import annotations

import argparse
import json
import sys

# Resources where a destroy is almost always a mistake, not an intended
# change — losing the cluster, the database, or the state lock table. Any
# destroy touching these requires an explicit, named human approver.
PROTECTED_RESOURCES = {
    "module.eks",
    "module.rds",
    "aws_db_instance.primary",
    "aws_dynamodb_table.terraform-state-locks",
    "aws_s3_bucket.terraform_state",
}


class PlanReviewError(PermissionError):
    pass


def _destroy_addresses(plan: dict) -> list[str]:
    return [
        change["address"]
        for change in plan.get("resource_changes", [])
        if "delete" in change.get("change", {}).get("actions", [])
    ]


def _touches_protected(address: str) -> bool:
    return any(protected in address for protected in PROTECTED_RESOURCES)


def review(plan: dict, approver: str | None) -> list[str]:
    """Return the list of destroy addresses if the plan is safe to apply,
    or raise PlanReviewError if it isn't.
    """
    destroys = _destroy_addresses(plan)
    protected_destroys = [addr for addr in destroys if _touches_protected(addr)]

    if protected_destroys and approver is None:
        raise PlanReviewError(
            "Blocked: plan destroys protected resource(s) "
            f"{protected_destroys} with no named human approver. "
            "Re-run with --approver \"<your name>\" after reviewing the plan."
        )

    return destroys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_json", help="Path to `terraform show -json` output")
    parser.add_argument("--approver", default=None, help="Human approver name, required for protected destroys")
    args = parser.parse_args()

    with open(args.plan_json, encoding="utf-8") as f:
        plan = json.load(f)

    try:
        destroys = review(plan, args.approver)
    except PlanReviewError as exc:
        print(f"GUARDRAIL BLOCKED: {exc}", file=sys.stderr)
        return 1

    if destroys:
        print(f"Plan contains {len(destroys)} destroy(s), approved by {args.approver}: {destroys}")
    else:
        print("Plan contains no destroys. Safe to apply after normal PR review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
