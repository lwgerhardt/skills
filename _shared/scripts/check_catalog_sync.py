#!/usr/bin/env python3
"""Compare or sync the canonical model catalog against a project copy.

Check mode exits nonzero and prints each differing JSON path, so drift is
detectable rather than silent. Sync mode overwrites the target with the
canonical file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CANONICAL = Path(__file__).resolve().parent.parent / "model-catalog.json"

# Keys that legitimately differ per copy: the canonical file names its own
# location and the copies it feeds.
IGNORED_TOP_LEVEL_KEYS = frozenset({"canonical_source", "synced_copies", "sync_command"})


def load(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"missing file: {path}")
    except json.JSONDecodeError as exc:
        sys.exit(f"invalid JSON in {path}: {exc}")


def diff(left: object, right: object, path: str = "") -> list[str]:
    """Report semantic differences as JSON paths, ignoring key order."""
    if isinstance(left, dict) and isinstance(right, dict):
        out: list[str] = []
        for key in sorted(set(left) | set(right)):
            if not path and key in IGNORED_TOP_LEVEL_KEYS:
                continue
            child = f"{path}.{key}" if path else key
            if key not in left:
                out.append(f"{child}: missing in canonical")
            elif key not in right:
                out.append(f"{child}: missing in target")
            else:
                out.extend(diff(left[key], right[key], child))
        return out

    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return [f"{path}: list length {len(left)} vs {len(right)}"]
        out = []
        for index, (lhs, rhs) in enumerate(zip(left, right)):
            out.extend(diff(lhs, rhs, f"{path}[{index}]"))
        return out

    if left != right:
        return [f"{path}: {left!r} vs {right!r}"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path, help="project copy to compare or overwrite")
    parser.add_argument("--sync", action="store_true", help="overwrite the target with the canonical catalog")
    args = parser.parse_args()

    target = args.target.expanduser()

    if args.sync:
        canonical_text = CANONICAL.read_text(encoding="utf-8")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(canonical_text, encoding="utf-8")
        print(f"synced {CANONICAL} -> {target}")
        return 0

    differences = diff(load(CANONICAL), load(target))
    if differences:
        print(f"catalog drift: {CANONICAL} vs {target}")
        for line in differences:
            print(f"  {line}")
        return 1

    print(f"catalogs match: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
