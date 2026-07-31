# Worker agent templates

Portable stubs for project subagent directories. Copy bindings into each repo; chief skills stay in `~/.claude/skills/`.

## Install

From this repo (paths relative to the skills checkout):

```bash
mkdir -p <project>/.claude/agents <project>/.cursor/agents
cp _shared/agent-templates/claude/*  <project>/.claude/agents/
cp _shared/agent-templates/cursor/*  <project>/.cursor/agents/
```

Copy only the platform the project uses; the validator does not require both.

## Rules

- **Roles are names; models are pins.** Every file sets `model`, and every file has to keep it. An agent with no `model` inherits the session model — under a frontier chief that puts recon on the expensive model silently. Dropping the pin is a defect, not a shorthand for "use the default".
- **Claude `Explore.md`** — capital E required. Overrides the built-in Explore agent so recon stays cheap under a frontier chief. This is the one name that breaks Claude Code's lowercase-and-hyphens convention, because it has to match the built-in exactly.
- **Cursor `explore.md`** — lowercase. Cheap Explore analog; pin `composer-2.5` so subagents do not inherit the chief model.
- **Identifiers are per platform.** Claude Code aliases (`haiku`, `opus`) and Cursor slugs (`composer-2.5`, `claude-opus-5-thinking-high`) are not interchangeable. See `MODEL-CATALOG.md`.
- **Read-only roles are enforced, not just described.** Claude uses `tools` / `disallowedTools`; Cursor uses `readonly: true`. The Cursor `verifier` deliberately stays writable — `readonly` blocks state-changing shell commands, and verification has to run tests.
- **Defaults come from `role_hints`** in `model-catalog.json`. Projects may escalate `verifier` or `executor` pins for high-risk work; templates ship the cheap defaults.

## Cross-client discovery

Cursor reads `.cursor/agents/`, `.claude/agents/`, and `.codex/agents/`; Claude Code reads only `.claude/agents/`. On a name collision `.cursor/` wins, so installing both sets is safe for the five shared roles. The exception is `Explore` — Claude-only, and pinned to `haiku`, which Cursor cannot select, so a Cursor session falls back to a compatible model without saying so.

## Validate

```bash
_shared/scripts/check_agent_templates.py                       # templates in this repo
_shared/scripts/check_agent_templates.py --target <project>    # installed copies
_shared/scripts/check_agent_templates.py --target <project> --platform both
```

Exits 0 when every agent in the directory pins a platform-appropriate model and the canonical roles match `role_hints`; exits 1 and prints drift lines on failure. Files other than the six canonical roles are checked for a `model` pin too — an unpinned agent inheriting a frontier session is the defect that actually costs money.

`--target` checks whichever agent directories exist. `--platform both` requires each one; `--platform claude|cursor` checks a single client.
