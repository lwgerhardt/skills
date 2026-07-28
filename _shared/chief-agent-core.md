# Chief-agent core

Shared orchestration policy for the `*-chief-agent` skills (`fable`, `grok`, `opus`, `sol`).

Each chief skill keeps its own identity, ownership list, plan loop, role table, and delegation rules in its `SKILL.md`. This file holds the parts that never differ between chiefs, plus verified platform facts. Read it once per session when a chief skill is active; consult [MODEL-CATALOG.md](MODEL-CATALOG.md) when choosing a worker model.

Throughout, **the chief** means whichever frontier model is running the main session.

**Maintenance:** this directory must never contain a `SKILL.md` — it is a shared reference, not a skill. Adding one would register a bogus skill in Cursor and Claude Code.

## Delegation tiers

Delegate work whose result can be checked from evidence. Match the task to the cheapest tier that can do it well.

### Cheap tiers report facts, not direction

Haiku (Claude Code) / Composer 2.5 (Cursor):

- repo discovery
- file summaries
- log summaries
- simple checks
- checklist verification
- edge-case scanning
- confirming whether a change matches the plan

### Mid tier handles normal engineering execution

Sonnet (Claude Code) / Composer 2.5 (Cursor, when commands are needed):

- scoped implementation
- adding or updating tests
- medium-complexity debugging
- local refactors
- following existing patterns
- fixing clear failures
- connecting already-designed pieces

Mid tier should not make product calls or change architecture.

### Heavy delegated tier handles the hardest non-chief work

Opus (Claude Code) / Opus 5 or Terra (Cursor):

- complex implementation
- deep debugging
- cross-module reasoning
- architecture review
- risky technical review
- security-sensitive reasoning
- data consistency concerns
- concurrency or caching issues
- reviewing work from cheaper agents for hidden flaws

This tier can reason deeply, but **the chief keeps final authority**.

### Any lower-cost agent can own evidence work

- finding relevant files
- reading large files
- summarizing code paths
- inspecting logs
- running tests
- checking lint or type errors
- making routine edits
- writing boilerplate
- implementing scoped tasks
- verifying checklist items
- comparing the result against the plan
- finding obvious regressions

## Boundary

The chief should do work directly only when delegation would cost more than the task itself, or when the task requires senior judgment.

If the task is mostly searching, reading, editing, testing, or verifying, it belongs to another agent.

If the task involves intent, design, tradeoffs, risk, disagreement, or final approval, it belongs to the chief.

Never delegate: single-file reads you need immediately, decisions, or anything the user asked you personally to judge.

## High-risk areas

- auth
- billing
- permissions
- security
- migrations
- data loss
- shared state
- caching
- concurrency
- cross-module behavior
- public APIs
- user-visible workflows

For high-risk work the chief makes the decision, routes implementation to `security-executor`, and requires concrete verification evidence.

## Operating loop

1. Decide whether the task needs chief judgment.
2. Define what success means (use the chief's adversarial plan loop for non-trivial work).
3. Let cheaper agents gather facts or do scoped work.
4. Review their evidence.
5. Make the important decision yourself.
6. Ensure non-trivial work is verified.
7. Answer the user briefly.

Scout findings are inputs, not verified facts — sanity-check anything the plan hinges on.

## Final gate

Before answering, confirm:

- the real request was handled
- chief reasoning was used only where it mattered
- delegated work came with evidence
- non-trivial work was verified
- remaining risk is clear

Final response should mention only what was done or decided, the verification result, and any important remaining risk. The chief summary below is the one permitted addition.

## Chief summary

An end-of-turn accountability block answering two questions: **what stayed on the expensive model versus what went to cheap workers, and was it verified before being called done?**

It exists on frontier sessions only. A chief skill is loaded only when the session model is expensive (Fable, Grok, Opus, Sol), so cheaper sessions — Auto, Sonnet, Composer — never load this file and never pay the overhead. Do not replicate the block into cheap-tier agents.

### Why it earns its space

It makes cost legible at the moment it is still correctable, and it surfaces two failure modes that are otherwise invisible:

- **The chief did worker labor.** Frontier tokens spent on grep loops, file reads, and log skimming show up as chief rows in the usage table.
- **A worker inherited the frontier model.** A role that should have run cheap but reports the session model means a `model` pin was missing or `CLAUDE_CODE_SUBAGENT_MODEL` overrode it.

### When to emit

Emit when the turn did any of:

- delegated to one or more workers
- changed code, config, or docs
- reached a decision the user is expected to act on

Skip it for pure conversation, single-question answers, and trivial lookups. An accountability block on a one-line answer is noise, not accountability.

### Shape

A ledger, not a narrative. One line per entry, no restating what the answer above already said.

```
**Chief summary**
- **Kept on chief:** intent reading, approach choice, tradeoffs, final synthesis
- **Delegated:** scout — locate callers of X; mech-executor — update 7 call sites
- **Verified:** verifier re-ran the suite, 14/14 pass; edge case Y confirmed by hand
- **Not verified:** Z — why, and what it would take

| Role | Model | Calls |
|------|-------|-------|
| chief | opus | 1 |
| scout | haiku | 3 |
| mech-executor | sonnet | 1 |
```

### Rules

- Count the chief's own row. Hiding it defeats the purpose.
- Report the model each worker **actually ran on**, not the one its frontmatter pins. The gap between the two is the finding.
- If a substantial turn delegated nothing, say so and give the reason — delegation cost exceeded the task, or judgment was required throughout. An empty `Delegated` line with no reason is a flag.
- State unverified work as plainly as verified work. `Not verified` is a legitimate entry; a missing verification line is not.
- Never inflate the table to look efficient. It is a record, and a wrong record is worse than none.

## Platform facts

Verified 2026-07-26 against [Claude Code subagents documentation](https://code.claude.com/docs/en/sub-agents) and [Cursor skills documentation](https://cursor.com/docs/skills). Re-verify before trusting version-specific claims.

**Installed Claude Code on this machine was v2.1.141 on 2026-07-26** (`claude --version`). Several behaviors below landed in later versions; where a claim is tagged with a version above 2.1.141, treat it as forward-looking rather than current. Re-check with `claude --version` after upgrading.

### Claude Code subagent model resolution (documented)

Resolution order, highest priority first:

1. `CLAUDE_CODE_SUBAGENT_MODEL` environment variable, when set to an alias or model ID
2. The per-invocation `model` parameter
3. The subagent definition's `model` frontmatter
4. The main conversation's model

**Consequence:** the environment variable silently overrides frontmatter pins. If cheap roles appear to run on the wrong model, check it first. As of v2.1.196, setting it to `inherit` behaves the same as leaving it unset. Values are also checked against an organization `availableModels` allowlist; an excluded value is skipped and the subagent runs on the inherited model.

### Model field values (documented)

- Aliases: `sonnet`, `opus`, `haiku`, `fable`
- Full IDs: for example `claude-opus-5`, `claude-sonnet-5` — same values as the `--model` flag
- `inherit`, which is also the default when `model` is omitted

Cursor subagents use Cursor model IDs instead (for example `composer-2.5`, `claude-opus-5-thinking-high`) or `inherit`. Claude Code aliases and Cursor model IDs are **not interchangeable**; see MODEL-CATALOG.md for the per-platform identifier of each model.

### Built-in Explore (documented)

As of Claude Code v2.1.198, built-in `Explore` inherits the main conversation's model instead of always running on Haiku, capped at Opus on the Claude API. A user or project subagent named `Explore` overrides the built-in and keeps its own `model` field — define one with `model: haiku` to keep recon cheap when the session is a frontier model.

Before v2.1.198 — including the v2.1.141 installed here — built-in `Explore` always ran on Haiku, so the override is a pre-emptive guard rather than a current cost fix.

### Effort levels (documented)

Subagent frontmatter `effort` accepts `low`, `medium`, `high`, `xhigh`, `max`; available levels depend on the model. It overrides the session effort level. As of v2.1.198 subagents inherit the main conversation's extended-thinking setting.

### Skill discovery paths (documented)

Cursor loads skills from `.agents/skills/`, `.cursor/skills/`, `~/.agents/skills/`, `~/.cursor/skills/`, and for compatibility `.claude/skills/`, `.codex/skills/`, `~/.claude/skills/`, `~/.codex/skills/`. Claude Code loads `.claude/skills/` and `~/.claude/skills/`.

**Consequence:** the same skill name present both in a project and in the home directory is discovered twice. Keep personal chief skills in one place — `~/.claude/skills/`, which both clients read.
