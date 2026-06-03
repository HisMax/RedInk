#!/usr/bin/env python3
"""
Resolve the current recommended XHS eval set from a release-gate manifest.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


RESOLUTION_SCHEMA_VERSION = "xhs_recommended_eval_set_resolution.v1"
RECOMMENDED_SCHEMA_VERSION = "xhs_recommended_eval_set.v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve the recommended XHS eval set path.")
    parser.add_argument("--recommended-manifest", required=True, help="Path to xhs-quality-cases.recommended.json.")
    parser.add_argument("--print-cases", action="store_true", help="Print only the resolved candidate cases path.")
    return parser.parse_args()


def resolve_recommended_eval_set(path: str | Path) -> Dict[str, Any]:
    """Resolve and validate a recommended eval set manifest."""
    manifest_path = Path(path)
    reasons: List[str] = []
    manifest: Dict[str, Any] = {}

    if not manifest_path.exists():
        reasons.append("recommended manifest does not exist")
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            reasons.append(f"recommended manifest is invalid JSON: {exc}")

    if manifest and manifest.get("schema_version") != RECOMMENDED_SCHEMA_VERSION:
        reasons.append("recommended manifest schema_version is invalid")

    gate = manifest.get("gate") or {}
    if manifest and (gate.get("eligible") is not True or gate.get("status") != "passed"):
        reasons.append("recommended manifest gate is not passed")

    candidate_cases = manifest.get("candidate_cases") if manifest else None
    if manifest and not candidate_cases:
        reasons.append("recommended manifest candidate_cases is missing")
    if candidate_cases and not Path(candidate_cases).exists():
        reasons.append("recommended candidate cases file does not exist")

    resolved = not reasons
    return {
        "schema_version": RESOLUTION_SCHEMA_VERSION,
        "recommended_manifest": str(manifest_path),
        "candidate_cases": str(candidate_cases or ""),
        "version_id": manifest.get("version_id"),
        "gate_status": gate.get("status"),
        "resolved": resolved,
        "reasons": reasons,
    }


def main() -> int:
    args = parse_args()
    payload = resolve_recommended_eval_set(args.recommended_manifest)
    if args.print_cases and payload["resolved"]:
        print(payload["candidate_cases"])
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["resolved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

