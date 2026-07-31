#!/usr/bin/env python3
"""Regression tests for check_agent_templates escalation policy."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from check_agent_templates import (  # noqa: E402
    NON_AGENT_FILES,
    TEMPLATES,
    check_canonical_agent,
    load_catalog,
    parse_frontmatter,
    validate_directory,
)

CHECK_SCRIPT = SCRIPT_DIR / "check_agent_templates.py"


def write_agent(path: Path, name: str, model: str) -> None:
    path.write_text(
        f"---\nname: {name}\ndescription: test\nmodel: {model}\n---\n",
        encoding="utf-8",
    )


def populate_canonical(
    directory: Path, platform: str, overrides: dict[str, str] | None = None
) -> None:
    """Seed a temp agents dir from the shipped templates; optionally re-pin roles."""
    overrides = overrides or {}
    for path in sorted((TEMPLATES / platform).glob("*.md")):
        if path.name.lower() in NON_AGENT_FILES:
            continue
        dest = directory / path.name
        if path.stem in overrides:
            name = parse_frontmatter(path.read_text(encoding="utf-8")).get(
                "name", path.stem
            )
            write_agent(dest, name, overrides[path.stem])
        else:
            shutil.copy2(path, dest)


class CanonicalTemplatesTest(unittest.TestCase):
    def test_canonical_templates_pass(self) -> None:
        catalog = load_catalog()
        for platform in ("claude", "cursor"):
            failures = validate_directory(TEMPLATES / platform, platform, catalog)
            self.assertEqual(failures, [], failures)

    def test_check_script_exits_zero_on_canonical_tree(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT), "--skip-symlinks"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class EscalationPolicyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = load_catalog()

    def assert_role_passes(self, platform: str, role: str, model: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            populate_canonical(directory, platform, {role: model})
            failures = validate_directory(directory, platform, self.catalog)
            self.assertEqual(failures, [], failures)

    def assert_role_fails(self, platform: str, role: str, model: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            populate_canonical(directory, platform, {role: model})
            failures = validate_directory(directory, platform, self.catalog)
            self.assertTrue(
                failures, f"expected failure for {platform}/{role} -> {model!r}"
            )
            self.assertTrue(
                any(f"{platform}/{role}.md" in line for line in failures),
                failures,
            )

    def test_claude_verifier_opus_escalation_passes(self) -> None:
        self.assert_role_passes("claude", "verifier", "opus")

    def test_cursor_executor_inherit_passes(self) -> None:
        self.assert_role_passes("cursor", "executor", "inherit")

    def test_cursor_scout_inherit_fails(self) -> None:
        self.assert_role_fails("cursor", "scout", "inherit")

    def test_cursor_executor_composer_downgrade_fails(self) -> None:
        self.assert_role_fails("cursor", "executor", "composer-2.5")

    def test_claude_verifier_haiku_downgrade_fails(self) -> None:
        self.assert_role_fails("claude", "verifier", "haiku")

    def test_unpinned_extra_agent_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            populate_canonical(directory, "cursor")
            (directory / "custom.md").write_text(
                "---\nname: custom\ndescription: test\n---\n",
                encoding="utf-8",
            )
            failures = validate_directory(directory, "cursor", self.catalog)
            self.assertTrue(
                any(
                    "custom.md" in line and "no 'model' pin" in line
                    for line in failures
                )
            )

    def test_unknown_model_on_escalatable_role_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            populate_canonical(directory, "claude", {"verifier": "not-a-real-model"})
            failures: list[str] = []
            check_canonical_agent(
                directory / "verifier.md",
                "claude",
                "verifier",
                self.catalog,
                failures,
            )
            self.assertTrue(failures)
            self.assertTrue(any("not in allowed" in line for line in failures))


if __name__ == "__main__":
    unittest.main()
