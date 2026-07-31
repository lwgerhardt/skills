# Chief-agent skills

Orchestrator skills for frontier-model coding agents, shared between Claude Code and
Cursor.

The premise: when the session model is expensive, its value is judgment, not labor.
These skills keep intent, architecture, adversarial plan review, tradeoffs, and final
synthesis with the chief, and push discovery, mechanical execution, tests, and
verification down to the cheapest role that can do the job — across model families, not
just the chief's vendor.

## Layout

```
_shared/
  chief-agent-core.md        policy identical across all chiefs
  MODEL-CATALOG.md           per-model tags, identifiers, pairwise guidance
  model-catalog.json         machine-readable canonical source
  agent-templates/
    claude/                  worker stubs for .claude/agents/
    cursor/                  worker stubs for .cursor/agents/
  scripts/
    check_catalog_sync.py    drift detection against a project copy
    check_agent_templates.py validate worker model pins vs role_hints
fable-chief-agent/
  SKILL.md
  references -> ../_shared
grok-chief-agent/
opus-chief-agent/
sol-chief-agent/
deputy-agent/
  SKILL.md                   the inverse — cheap session, frontier subagents
  references -> ../_shared
spinoff/
  SKILL.md                   workflow skill, not a chief — see below
```

Each chief `SKILL.md` holds only what is genuinely per-chief: identity, ownership list,
adversarial plan loop, role table, delegation rules. Everything identical across chiefs
lives once in `_shared/chief-agent-core.md` and is reached through the `references`
symlink, so the four skills cannot drift apart on shared policy.

`deputy-agent/` covers the opposite situation from the chiefs: the session model is
cheap or mid, but frontier subagents are reachable. It is not a mirrored chief skill,
because the inversion is not symmetric — a cheap model cannot reliably judge whether a
task exceeds its own competence, and cannot fully evaluate the frontier output it gets
back. So it escalates on **observable triggers** (category, failed-attempt count, blast
radius) rather than self-assessment, and it does not re-judge what comes back. Final
authority moves to the escalated subagent; in the chief skills it stays with the
session. One skill for every cheap model rather than one per model, since the policy
does not vary by which cheap model is running.

Matters most for sessions nobody chose the model for — spun-off tasks, scheduled runs,
cloud agents — which land on whatever the host defaults to.

`spinoff/` is the other non-chief skill: a workflow, invoked by any model, for handing a
workstream to a fresh agent session. It belongs here rather than in a project because it
hardcodes no repo's layout or policy — it discovers them. It pairs naturally with the
chief skills, since deciding what to hand off and what to keep is exactly the judgment
call a chief owns.

`_shared/` deliberately contains no `SKILL.md`. Adding one would register a bogus skill
in both clients.

## Install

Clone into the skills directory that both clients read:

```
git clone https://github.com/lwgerhardt/skills.git ~/.claude/skills
```

If `~/.claude/skills` already exists, clone elsewhere and copy the four
`*-chief-agent/` directories plus `_shared/` into it, preserving the symlinks
(`cp -R` does).

Install in exactly one location. Claude Code reads `.claude/skills/` and
`~/.claude/skills/`; Cursor reads those plus `.agents/skills/`, `.cursor/skills/`,
`~/.agents/skills/`, `~/.cursor/skills/`, `.codex/skills/`, and `~/.codex/skills/`. The
same skill name present in both a project and the home directory is discovered twice,
and you will spend an afternoon editing the copy that isn't loading.

## Using them

Invoke the chief matching the active session model — `opus-chief-agent` when running
Opus, `sol-chief-agent` when running Sol, and so on. The skill then governs what the
chief does directly versus what it delegates.

Roles are names, not models. `scout`, `mech-executor`, `executor`, `verifier`, and
`security-executor` are bound to actual models in subagent frontmatter under
`.claude/agents/` or `.cursor/agents/`. `MODEL-CATALOG.md` is what you consult to
choose a binding; the skills themselves never hardcode one.

## Worker agent templates

Chief skills install once in `~/.claude/skills/`. Model bindings are per-project:
copy the stubs into each repo's agent directories.

```bash
cp _shared/agent-templates/claude/*  <project>/.claude/agents/
cp _shared/agent-templates/cursor/*  <project>/.cursor/agents/
```

Templates pin models from `role_hints` in `model-catalog.json`. Omit `model` in
frontmatter and cheap roles inherit the frontier session — the templates always set
it. Claude `Explore.md` (capital E) overrides the built-in Explore agent; Cursor uses
`explore.md` (lowercase) as the cheap analog.

Validate the canonical templates or an installed project copy:

```bash
_shared/scripts/check_agent_templates.py
_shared/scripts/check_agent_templates.py --target <project>
```

Exits nonzero on missing roles, wrong `name`, or model pins that drift from
`role_hints`. Projects may escalate `verifier` or `executor` pins; the templates ship
the cheap defaults.

## Chief summary

Frontier sessions close a turn with a short accountability ledger: what stayed on the
expensive model, what went to which worker, whether it was verified, and a table
counting calls by role and model.

It exists to make cost legible while it is still correctable, and to expose two failure
modes that are otherwise invisible — the chief doing worker labor like grep loops and
file reads, and a worker silently inheriting the frontier model because a `model` pin
was missing or overridden. The table reports the model each worker *actually ran on*,
not the one its frontmatter claims; the gap between the two is the finding.

Cheap sessions never load a chief skill, so they never pay the overhead. The block is
skipped for conversation and trivial lookups — an accountability block on a one-line
answer is noise, not accountability. Full rules are in `_shared/chief-agent-core.md`.

## Evidence tiers

Capability claims age badly, so every one is graded:

- `documented` — stated in official vendor documentation
- `observed` — seen in a live client on the recorded verification date
- `heuristic` — operating judgment, expect drift

Both shared documents carry a `last_verified` date. `model-catalog.json` also records
the client version observed at verification time, and any behavior belonging to a later
version is marked forward-looking rather than asserted as current. Re-check and re-date
after upgrading rather than trusting the file.

Two platform behaviors worth knowing before you debug a cost surprise:

- Subagent model resolution runs `CLAUDE_CODE_SUBAGENT_MODEL` > per-invocation `model`
  > frontmatter > session model. The environment variable **silently overrides
  frontmatter pins** — check it first when a cheap role appears to run on the wrong
  model.
- Built-in `Explore` inherits the session model in recent versions rather than always
  running cheap. Define a project `Explore` agent pinned to a cheap model to keep recon
  cheap under a frontier chief.

## Keeping copies in sync

If a project keeps a committed copy of the catalog for repo-local tooling:

```
_shared/scripts/check_catalog_sync.py --target <path>          # check, nonzero on drift
_shared/scripts/check_catalog_sync.py --target <path> --sync   # canonical -> copy
```

The check is a semantic JSON diff — key-order-insensitive, and it ignores the keys that
legitimately differ per copy. Markdown copies are intentionally project-aware and are
not byte-compared.

## Scope

This repo is the general, portable half. Project-specific orchestration — routing,
handoffs, active work — belongs in a per-repo catalog, not in copied chief skills.
Model bindings belong in per-repo agent frontmatter.

## License

MIT. See `LICENSE`.
