#!/usr/bin/env python3
"""Validate worker agent templates against model-catalog role_hints.

Check mode exits nonzero and prints each drift line. Default validates the
canonical template tree under _shared/agent-templates/.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SHARED = Path(__file__).resolve().parent.parent
REPO_ROOT = SHARED.parent
CATALOG = SHARED / "model-catalog.json"
TEMPLATES = SHARED / "agent-templates"

CLAUDE_ROLES: tuple[str, ...] = (
    "scout",
    "Explore",
    "mech-executor",
    "executor",
    "verifier",
    "security-executor",
)
CURSOR_ROLES: tuple[str, ...] = (
    "scout",
    "explore",
    "mech-executor",
    "executor",
    "verifier",
    "security-executor",
)

# Short hints from role_hints -> acceptable model field values.
HINT_TO_MODELS: dict[str, frozenset[str]] = {
    "haiku": frozenset({"haiku"}),
    "sonnet": frozenset({"sonnet"}),
    "opus": frozenset({"opus", "claude-opus-5", "claude-opus-5-thinking-high"}),
    "composer-2.5": frozenset({"composer-2.5"}),
    "terra": frozenset({"terra", "gpt-5.6-terra-medium"}),
    "inherit": frozenset({"inherit"}),
}

# Explore/explore are not separate role_hints entries; they share scout's tier.
EXPLORE_ROLE = {"Explore": "scout", "explore": "scout"}


def load_catalog() -> dict:
    try:
        return json.loads(CATALOG.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"missing catalog: {CATALOG}")
    except json.JSONDecodeError as exc:
        sys.exit(f"invalid JSON in {CATALOG}: {exc}")


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse simple YAML frontmatter (key: value lines only)."""
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    end: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = index
            break
    if end is None:
        return {}
    out: dict[str, str] = {}
    for line in lines[1:end]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def role_filename(role: str) -> str:
    return f"{role}.md"


def expected_name(role: str) -> str:
    return role


def allowed_models(catalog: dict, platform: str, role: str) -> frozenset[str]:
    role_hints: dict = catalog.get("role_hints", {})
    hint_role = EXPLORE_ROLE.get(role, role)
    entry = role_hints.get(hint_role)
    if not entry:
        return frozenset()

    allowed: set[str] = set()
    primary = entry.get(platform)
    if primary:
        allowed |= HINT_TO_MODELS.get(primary, {primary})

    alternate = entry.get("cursor_alternate")
    if platform == "cursor" and alternate:
        allowed |= HINT_TO_MODELS.get(alternate, {alternate})

    return frozenset(allowed)


def check_agent_file(
    path: Path,
    platform: str,
    role: str,
    catalog: dict,
    failures: list[str],
) -> None:
    label = f"{platform}/{path.name}"
    if not path.is_file():
        failures.append(f"{label}: missing file")
        return

    frontmatter = parse_frontmatter(path.read_text(encoding="utf-8"))
    if not frontmatter:
        failures.append(f"{label}: missing or invalid YAML frontmatter")
        return

    name = frontmatter.get("name")
    model = frontmatter.get("model")
    expected = expected_name(role)

    if not name:
        failures.append(f"{label}: missing frontmatter 'name'")
    elif name != expected:
        failures.append(f"{label}: name {name!r} != expected {expected!r}")

    if not model:
        failures.append(f"{label}: missing frontmatter 'model' (cheap roles inherit session)")
        return

    allowed = allowed_models(catalog, platform, role)
    if allowed and model not in allowed:
        failures.append(
            f"{label}: model {model!r} not in allowed {sorted(allowed)!r} for role {role!r}"
        )


def validate_directory(
    directory: Path,
    platform: str,
    roles: tuple[str, ...],
    catalog: dict,
) -> list[str]:
    failures: list[str] = []
    for role in roles:
        check_agent_file(directory / role_filename(role), platform, role, catalog, failures)
    return failures


def check_references_symlinks(failures: list[str]) -> None:
    expected_target = SHARED.resolve()
    candidates: list[Path] = list(REPO_ROOT.glob("*-chief-agent"))
    deputy = REPO_ROOT / "deputy-agent"
    if deputy.is_dir():
        candidates.append(deputy)

    for agent_dir in sorted(candidates):
        ref = agent_dir / "references"
        label = ref.relative_to(REPO_ROOT)
        if not ref.exists():
            failures.append(f"{label}: missing (expected symlink to ../_shared)")
            continue
        if not ref.is_symlink():
            failures.append(f"{label}: not a symlink (expected -> ../_shared)")
            continue
        try:
            resolved = ref.resolve()
        except OSError as exc:
            failures.append(f"{label}: broken symlink ({exc})")
            continue
        if resolved != expected_target:
            failures.append(
                f"{label}: points to {resolved}, expected {expected_target}"
            )


def resolve_agent_dirs(args: argparse.Namespace) -> tuple[Path | None, Path | None]:
    claude_dir = args.claude_dir
    cursor_dir = args.cursor_dir

    if args.target is not None:
        target = args.target.expanduser().resolve()
        if claude_dir is None:
            claude_dir = target / ".claude" / "agents"
        if cursor_dir is None:
            cursor_dir = target / ".cursor" / "agents"

    if claude_dir is None and cursor_dir is None:
        claude_dir = TEMPLATES / "claude"
        cursor_dir = TEMPLATES / "cursor"

    if claude_dir is not None:
        claude_dir = claude_dir.expanduser().resolve()
    if cursor_dir is not None:
        cursor_dir = cursor_dir.expanduser().resolve()

    return claude_dir, cursor_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        type=Path,
        help="project root containing .claude/agents and .cursor/agents",
    )
    parser.add_argument("--claude-dir", type=Path, help="override Claude agents directory")
    parser.add_argument("--cursor-dir", type=Path, help="override Cursor agents directory")
    parser.add_argument(
        "--skip-symlinks",
        action="store_true",
        help="skip chief/deputy references -> _shared symlink check",
    )
    args = parser.parse_args()

    catalog = load_catalog()
    claude_dir, cursor_dir = resolve_agent_dirs(args)
    failures: list[str] = []

    validating_templates = (
        claude_dir == (TEMPLATES / "claude").resolve()
        and cursor_dir == (TEMPLATES / "cursor").resolve()
    )

    if claude_dir is not None:
        if not claude_dir.is_dir():
            failures.append(f"claude agents dir missing: {claude_dir}")
        else:
            failures.extend(validate_directory(claude_dir, "claude", CLAUDE_ROLES, catalog))

    if cursor_dir is not None:
        if not cursor_dir.is_dir():
            failures.append(f"cursor agents dir missing: {cursor_dir}")
        else:
            failures.extend(validate_directory(cursor_dir, "cursor", CURSOR_ROLES, catalog))

    if validating_templates and not args.skip_symlinks:
        check_references_symlinks(failures)

    if failures:
        print("agent template drift:")
        for line in failures:
            print(f"  {line}")
        return 1

    parts: list[str] = []
    if claude_dir is not None:
        parts.append(f"claude={claude_dir}")
    if cursor_dir is not None:
        parts.append(f"cursor={cursor_dir}")
    print(f"agent templates OK ({', '.join(parts)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
