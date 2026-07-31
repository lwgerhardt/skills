#!/usr/bin/env python3
"""Validate worker agent templates against model-catalog role_hints.

Check mode exits nonzero and prints each drift line. Default validates the
canonical template tree under _shared/agent-templates/.

Allowed model values are derived from model-catalog.json rather than restated
here: a role_hint names a catalog model key, and the identifiers valid for a
platform come from that model's claude_code_alias / claude_code_model_id /
cursor_model_id. A hint that names a missing model, or a model with no
identifier on the platform it is bound to, is a failure rather than a skip.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SHARED = Path(__file__).resolve().parent.parent
REPO_ROOT = SHARED.parent
CATALOG = SHARED / "model-catalog.json"
TEMPLATES = SHARED / "agent-templates"

CANONICAL_ROLES: dict[str, tuple[str, ...]] = {
    "claude": (
        "scout",
        "Explore",
        "mech-executor",
        "executor",
        "verifier",
        "security-executor",
    ),
    "cursor": (
        "scout",
        "explore",
        "mech-executor",
        "executor",
        "verifier",
        "security-executor",
    ),
}

# Explore/explore are not separate role_hints entries; they share scout's tier.
EXPLORE_ROLE = {"Explore": "scout", "explore": "scout"}

INHERIT = "inherit"

# Cursor accepts model parameters in bracket notation, e.g.
# claude-opus-5-thinking-high[effort=high,context=300k].
MODEL_PARAMS = re.compile(r"\[[^\]]*\]\s*$")

# Files in an agents directory that are not agent definitions.
NON_AGENT_FILES = {"readme.md"}

PLATFORM_ID_FIELDS: dict[str, tuple[str, ...]] = {
    "claude": ("claude_code_alias", "claude_code_model_id"),
    "cursor": ("cursor_model_id",),
}


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


def normalize_model(value: str) -> str:
    """Drop Cursor's bracket model parameters so the base ID can be compared."""
    return MODEL_PARAMS.sub("", value).strip()


def model_identifiers(catalog: dict, model_key: str, platform: str) -> frozenset[str]:
    """Identifiers a platform accepts for a catalog model. Empty when unavailable."""
    entry = catalog.get("models", {}).get(model_key)
    if not entry:
        return frozenset()
    ids = {entry.get(field) for field in PLATFORM_ID_FIELDS[platform]}
    return frozenset(i for i in ids if i)


def platform_identifiers(catalog: dict, platform: str) -> frozenset[str]:
    """Every identifier valid on a platform, across all catalog models."""
    ids: set[str] = set()
    for model_key in catalog.get("models", {}):
        ids |= model_identifiers(catalog, model_key, platform)
    return frozenset(ids)


def foreign_identifiers(catalog: dict, platform: str) -> frozenset[str]:
    """Identifiers that belong to another platform and never to this one.

    The catalog's schema_notes require platform identifiers stay distinct; a
    Cursor slug pinned inside .claude/agents is drift, not a synonym.
    """
    others = {p for p in PLATFORM_ID_FIELDS if p != platform}
    foreign: set[str] = set()
    for other in others:
        foreign |= platform_identifiers(catalog, other)
    return frozenset(foreign - platform_identifiers(catalog, platform))


def hint_values(catalog: dict, platform: str, role: str) -> tuple[list[str], list[str]]:
    """Catalog model keys bound to (platform, role), plus any catalog errors."""
    hint_role = EXPLORE_ROLE.get(role, role)
    entry = catalog.get("role_hints", {}).get(hint_role)
    if not entry:
        return [], [f"role_hints has no entry for role {hint_role!r}"]

    values: list[str] = []
    primary = entry.get(platform)
    if not primary:
        return [], [f"role_hints[{hint_role!r}] has no {platform!r} binding"]
    values.append(primary)

    alternate = entry.get(f"{platform}_alternate")
    if alternate:
        values.append(alternate)
    return values, []


def allowed_models(
    catalog: dict, platform: str, role: str
) -> tuple[frozenset[str], list[str]]:
    """Resolve a role's allowed model values. Errors mean the catalog is wrong."""
    values, errors = hint_values(catalog, platform, role)
    if errors:
        return frozenset(), errors

    allowed: set[str] = set()
    for value in values:
        if value == INHERIT:
            allowed.add(INHERIT)
            continue
        if value not in catalog.get("models", {}):
            errors.append(
                f"role_hints binds {role!r} to {value!r}, which is not a catalog model"
            )
            continue
        ids = model_identifiers(catalog, value, platform)
        if not ids:
            errors.append(
                f"role_hints binds {role!r} to {value!r}, which has no {platform} identifier"
            )
            continue
        allowed |= set(ids)

    return frozenset(allowed), errors


def check_canonical_agent(
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
    if not name:
        failures.append(f"{label}: missing frontmatter 'name'")
    elif name != role:
        failures.append(f"{label}: name {name!r} != expected {role!r}")

    model = frontmatter.get("model")
    if not model:
        failures.append(
            f"{label}: no 'model' pin, so this role will inherit the session model "
            f"and run at chief price; pin it"
        )
        return

    allowed, errors = allowed_models(catalog, platform, role)
    failures.extend(f"{label}: {error}" for error in errors)
    if errors:
        return

    if normalize_model(model) not in allowed:
        failures.append(
            f"{label}: model {model!r} not in allowed {sorted(allowed)!r} for role {role!r}"
        )


def check_extra_agent(
    path: Path,
    platform: str,
    catalog: dict,
    failures: list[str],
) -> None:
    """Every other agent file in the directory still has to pin a model.

    Unpinned agents are exactly the defect the chief skills warn about: they
    inherit the frontier session. Their model is not matched against role_hints
    (the role is unknown), but it must exist and belong to this platform.
    """
    label = f"{platform}/{path.name}"
    frontmatter = parse_frontmatter(path.read_text(encoding="utf-8"))
    if not frontmatter:
        failures.append(f"{label}: missing or invalid YAML frontmatter")
        return

    if platform == "claude" and not frontmatter.get("name"):
        failures.append(f"{label}: missing frontmatter 'name'")

    model = frontmatter.get("model")
    if not model:
        failures.append(
            f"{label}: no 'model' pin, so this agent will inherit the session model "
            f"and run at chief price; pin it"
        )
        return

    base = normalize_model(model)
    if base in foreign_identifiers(catalog, platform):
        failures.append(
            f"{label}: model {model!r} is another platform's identifier; "
            f"use the {platform} identifier from model-catalog.json"
        )


def validate_directory(
    directory: Path,
    platform: str,
    catalog: dict,
) -> list[str]:
    failures: list[str] = []
    roles = CANONICAL_ROLES[platform]

    canonical_paths: set[Path] = set()
    for role in roles:
        path = directory / f"{role}.md"
        canonical_paths.add(path)
        check_canonical_agent(path, platform, role, catalog, failures)

    for path in sorted(directory.rglob("*.md")):
        if path in canonical_paths or path.name.lower() in NON_AGENT_FILES:
            continue
        check_extra_agent(path, platform, catalog, failures)

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
            failures.append(f"{label}: points to {resolved}, expected {expected_target}")


def resolve_agent_dirs(args: argparse.Namespace) -> dict[str, Path]:
    """Map platform -> directory for every platform this run should check."""
    explicit: dict[str, Path] = {}
    if args.claude_dir is not None:
        explicit["claude"] = args.claude_dir
    if args.cursor_dir is not None:
        explicit["cursor"] = args.cursor_dir

    if args.target is not None:
        target = args.target
        explicit.setdefault("claude", target / ".claude" / "agents")
        explicit.setdefault("cursor", target / ".cursor" / "agents")

    if not explicit:
        explicit = {"claude": TEMPLATES / "claude", "cursor": TEMPLATES / "cursor"}

    return {
        platform: path.expanduser().resolve() for platform, path in explicit.items()
    }


def selected_platforms(args: argparse.Namespace, dirs: dict[str, Path]) -> list[str]:
    if args.platform in ("claude", "cursor"):
        return [args.platform]
    return [p for p in ("claude", "cursor") if p in dirs]


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
        "--platform",
        choices=("auto", "claude", "cursor", "both"),
        default="auto",
        help=(
            "which platforms must be present. 'auto' (default) checks whichever "
            "agent directories exist and fails only when none do; 'both' requires "
            "each one; 'claude'/'cursor' check just that platform"
        ),
    )
    parser.add_argument(
        "--skip-symlinks",
        action="store_true",
        help="skip chief/deputy references -> _shared symlink check",
    )
    args = parser.parse_args()

    catalog = load_catalog()
    dirs = resolve_agent_dirs(args)
    platforms = selected_platforms(args, dirs)
    failures: list[str] = []
    checked: list[str] = []
    skipped: list[str] = []

    # Explicit paths and --platform pins are assertions the directory exists;
    # under 'auto' a project may legitimately use only one client.
    required = {
        p
        for p in platforms
        if args.platform in ("both", "claude", "cursor")
        or (p == "claude" and args.claude_dir is not None)
        or (p == "cursor" and args.cursor_dir is not None)
    }

    for platform in platforms:
        directory = dirs.get(platform)
        if directory is None:
            failures.append(f"{platform}: no agents directory resolved")
            continue
        if not directory.is_dir():
            if platform in required:
                failures.append(f"{platform} agents dir missing: {directory}")
            else:
                skipped.append(f"{platform}={directory}")
            continue
        failures.extend(validate_directory(directory, platform, catalog))
        checked.append(f"{platform}={directory}")

    if not checked and not failures:
        failures.append(
            "no agent directories found: "
            + ", ".join(f"{p}={dirs[p]}" for p in platforms)
        )

    validating_templates = all(
        dirs.get(platform) == (TEMPLATES / platform).resolve()
        for platform in ("claude", "cursor")
    )
    if validating_templates and not args.skip_symlinks:
        check_references_symlinks(failures)

    if failures:
        print("agent template drift:")
        for line in failures:
            print(f"  {line}")
        return 1

    message = f"agent templates OK ({', '.join(checked)})"
    if skipped:
        message += f" [not present: {', '.join(skipped)}]"
    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
