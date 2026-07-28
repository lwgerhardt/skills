# Model catalog

Machine-readable source: [model-catalog.json](model-catalog.json) — canonical copy lives here (`~/.claude/skills/_shared/`).

Chief-agent skills use **roles** and **tiers** at runtime. This catalog adds **per-model tags** so orchestrators pick a worker model for a reason, not by habit.

**Last verified 2026-07-26.** Identifiers are documented or observed; capability guidance is operating judgment and ages fastest. Check the `evidence` block on a model before relying on it in a new setup.

## Identifiers are platform-specific

Never substitute one platform's identifier for another's.

| Field | Meaning |
|-------|---------|
| `claude_code_alias` | Short alias accepted by Claude Code (`sonnet`, `opus`, `haiku`, `fable`) |
| `claude_code_model_id` | Full Claude Code model ID (for example `claude-opus-5`) |
| `cursor_model_id` | Slug selectable in Cursor (for example `claude-opus-5-thinking-high`) |
| `null` | Not available on that platform, or not verified — see `evidence` |

`opus`, `claude-opus-5`, and `claude-opus-5-thinking-high` are three different strings for three different contexts.

## Tag fields

| Field | Meaning |
|-------|---------|
| `tier` | `cheap` → `mid` → `capable` → `frontier` (cost/latency band) |
| `platforms` | Where the model is selectable (`cursor`, `claude`) |
| `strengths` | Capability tags — match task type to model |
| `weaknesses` | Do not delegate these here |
| `prefer_for` / `avoid_for` | Human-readable role guidance |
| `evidence` | How identifier and capability claims were established, and when |

**Strength tags:** `recon`, `read-summarize`, `checklist-verify`, `run-commands`, `mechanical-edit`, `scoped-implementation`, `multi-file-implementation`, `debugging`, `cross-module-reasoning`, `architecture`, `adversarial-review`, `planning`, `security`, `final-synthesis`

**Evidence kinds:** `documented` (official vendor docs), `observed` (seen in a live client on the verification date), `heuristic` (operating judgment; expect drift).

## Quick tier map

| Tier | Models | Typical roles |
|------|--------|---------------|
| **cheap** | Haiku, Composer 2.5, Composer 2.5 Fast | scout, mech-executor, verifier |
| **mid** | Sonnet | scoped implementation, verify (Claude Code) |
| **capable** | Terra, Sol | executor (Cursor), heavy delegated slices |
| **frontier** | Fable, Opus 5, Grok | chief session; Opus 5 also serves as Cursor executor |

Delegation is **cross-family** — the chief's vendor does not constrain the worker model. Pick the cheapest model whose **strengths** match the task and whose **platform** matches where you are working.

## Haiku vs Composer 2.5

The most common confusion: both are cheap, both do recon — **platform and toolchain** decide.

| Choose **Haiku** when | Choose **Composer 2.5** when |
|------------------------|------------------------------|
| Working in **Claude Code** | Working in **Cursor** |
| Read-only scout (grep, read, summarize) | Verifier must **run tests/scripts** |
| Minimal tokens on pure lookup | Mechanical **edits + shell** in one pass |
| Claude subagent with read-only tools | Chief is any family but subagents run in Cursor |

**Either is fine:** summarizing a code path you already located; checklist verify against a written plan with no commands.

Composer is not "smarter" than Haiku for lookup — it has **Cursor agent tooling** (shell, edit, terminal). Haiku is not "weaker" — it is the right cheap tier **inside Claude Code** where Composer is not spawnable.

## Other pairwise choices

**Sonnet vs Composer 2.5** — same mid execution band. Sonnet for Claude Code `mech-executor`; Composer when implementation must run repo commands in Cursor.

**Opus 5 vs Terra** — both heavy delegated implementation. Opus 5 in Claude Code (`opus`) or Cursor (`claude-opus-5-thinking-high`) when reasoning depth matters most; Terra (`gpt-5.6-terra-medium`) in Cursor when `inherit` would burn Grok/Sol/Fable tokens at a lower ceiling of need.

## Role → default model

From `role_hints` in the JSON:

| Role | Claude Code | Cursor |
|------|-------------|--------|
| scout / Explore | Haiku | Composer 2.5 |
| mech-executor | Sonnet | Composer 2.5 |
| executor | Opus 5 | Terra (or Opus 5) |
| verifier | Sonnet | Composer 2.5 |
| security-executor | Opus 5 | inherit (chief reviews) |
| chief | Fable / Opus 5 | Grok / Sol / Fable / Opus 5 |

## Platform behavior that changes cost

Full detail in [chief-agent-core.md](chief-agent-core.md) and `platform_facts` in the JSON.

- **Claude Code model resolution:** `CLAUDE_CODE_SUBAGENT_MODEL` > per-invocation `model` > frontmatter > session. The environment variable **silently overrides frontmatter pins** — check it first when a cheap role appears to run on the wrong model.
- **Built-in `Explore`** inherits the session model as of v2.1.198. Define a project/user `Explore` agent with `model: haiku` to keep recon cheap.
- **Skill discovery** covers both project and home directories, so a duplicated skill name loads twice.

## Keeping copies in sync

The canonical JSON is here; a project may keep a committed copy (for example `<project>/docs/agent-rules/model-catalog.json`) for repo-local tooling.

```bash
# check for drift (nonzero exit lists differing JSON paths)
~/.claude/skills/_shared/scripts/check_catalog_sync.py \
  --target ~/Projects/<project>/docs/agent-rules/model-catalog.json

# push canonical → project copy
~/.claude/skills/_shared/scripts/check_catalog_sync.py \
  --target ~/Projects/<project>/docs/agent-rules/model-catalog.json --sync
```

Markdown copies are intentionally project-aware and are not byte-compared; when identifiers change, update both Markdown files by hand.

## Related

- Shared orchestration policy: [chief-agent-core.md](chief-agent-core.md)
- Chief skills: `~/.claude/skills/*-chief-agent/SKILL.md`
- **Per-project orchestration:** each repo's `docs/agent-rules/PROJECT-AGENT-CATALOG.md` when present (routing, handoffs, active work — not model facts)
- Subagent pins: `.cursor/agents/`, `.claude/agents/` in each project
