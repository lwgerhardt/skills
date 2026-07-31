# Worker agent templates

Portable stubs for project subagent directories. Copy bindings into each repo; chief skills stay in `~/.claude/skills/`.

## Install

From this repo (paths relative to the skills checkout):

```bash
mkdir -p <project>/.claude/agents <project>/.cursor/agents
cp _shared/agent-templates/claude/*  <project>/.claude/agents/
cp _shared/agent-templates/cursor/*  <project>/.cursor/agents/
```

## Rules

- **Roles are names; models are pins.** Every file must set `model`. Omit it and cheap roles inherit the frontier session.
- **Claude `Explore.md`** — capital E required. Overrides the built-in Explore agent so recon stays cheap under a frontier chief.
- **Cursor `explore.md`** — lowercase. Cheap Explore analog; pin `composer-2.5` so subagents do not inherit the chief model.
- **Defaults come from `role_hints`** in `model-catalog.json`. Projects may escalate `verifier` or `executor` pins for high-risk work; templates ship the cheap defaults.

## Validate

```bash
_shared/scripts/check_agent_templates.py                    # templates in this repo
_shared/scripts/check_agent_templates.py --target <project> # installed copies
```

Exits 0 when pins match `role_hints`; exits 1 and prints drift lines on failure.
