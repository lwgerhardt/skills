# Handoff: sanctioned pin escalations in `check_agent_templates.py`

**Status:** nothing started. First session produces a written decision on the `inherit`
question below, then implements it. Verified 2026-07-31 against `main` at `f9f3319`.

**Job:** teach the template validator to distinguish a *sanctioned escalation* from
*drift*, so projects that deliberately pin a role above its `role_hints` default stop
failing the check.

Handed off now because the validator shipped in #1 is only usable on installs that took
the defaults verbatim. Every real install on this machine escalates something, so the
check currently fails everywhere it matters — it validates the templates and nothing
else.

## What exists today (verified 2026-07-31)

| Thing | Where | State |
|---|---|---|
| Validator | `_shared/scripts/check_agent_templates.py` | Ships on `main`; exits 0 on the canonical tree |
| Pin comparison | `check_agent_templates.py:216` | Literal string match against the allowed set |
| Allowed-set derivation | `check_agent_templates.py:151` (`allowed_models`) | Derived from catalog identifiers, per platform |
| Escalation *permitted* by policy | `README.md:129`, `_shared/agent-templates/README.md:24` | "Projects may escalate `verifier` or `executor` pins for high-risk work" |
| Escalation *instructed* by policy | `fable-chief-agent/SKILL.md:58` | "Escalate `verifier` one tier (`opus` in Claude Code, `inherit` in Cursor)" |
| Escalation *expressible* to the validator | — | **DOES NOT EXIST.** No flag, no override file, no frontmatter marker |
| Per-role tier data | `_shared/model-catalog.json` → `models.*.tier` | Present: `cheap`, `mid`, `capable`, `frontier` |
| Tier ordering | `_shared/model-catalog.json` → `tag_vocab.tier` | Present, and already in ascending order |
| Test suite for the validator | — | **DOES NOT EXIST.** Verified by hand-run cases only |

Two consumer projects on this machine have full six-role installs on both platforms.
Both fail with the identical pair of lines:

```
claude/verifier.md: model 'opus' not in allowed ['claude-sonnet-5', 'sonnet']
cursor/executor.md: model 'inherit' not in allowed ['claude-opus-5-thinking-high', 'gpt-5.6-terra-medium']
```

Neither is rot. The first is exactly the escalation `fable-chief-agent/SKILL.md:58`
tells chiefs to make. The second is `inherit` on a Cursor executor, which under a
frontier chief resolves to the frontier model — semantically the same thing
`role_hints.executor.cursor_alternate` already sanctions.

## Load-bearing unknown: what does `inherit` mean to a static checker?

This one changes the shape of the solution, so settle it before drafting.

`inherit` has no tier. Its cost depends entirely on the session model, which the
validator cannot see. On a Cursor `executor` under a frontier chief it is correct; on a
`scout` under the same chief it is the exact defect the whole system exists to prevent.
Same literal value, opposite verdicts, and the deciding fact is not in the repo.

**Experiment, before choosing a mechanism:** pin a Cursor subagent to `inherit`, spawn
it from sessions on two different models, and confirm what it actually resolves to in
each. Do not take this from the docs — Cursor documents a fallback path for
unavailable models, and the interaction between that fallback and `inherit` is not
stated. Also check `CLAUDE_CODE_SUBAGENT_MODEL` on the machine first: it silently
overrides frontmatter and would invalidate the observation.

The plausible resolutions, in rough order of preference:

1. **Tier-aware comparison.** Accept a pin whose catalog `tier` is at or above the
   `role_hints` default; reject downgrades. Needs no new syntax and encodes the actual
   policy. `tag_vocab.tier` already gives the ordering. Leaves `inherit` unresolved,
   which is why the experiment comes first.
2. **Per-role `inherit` policy.** Allow `inherit` on `executor` and `security-executor`,
   reject it on `scout` / `Explore` / `mech-executor` / `verifier`. Encodes intent
   directly; independent of tier work, and possibly sufficient on its own.
3. **Frontmatter rationale marker.** A key such as `pin_rationale:` that permits a
   non-default pin and records *why* in the file. Requires confirming both clients
   ignore unknown frontmatter keys — verify empirically in each, do not assume.
4. **Per-project override file.** Most expressive, most machinery, another format to
   keep in sync. Prefer only if 1–3 prove insufficient.

A bare `--allow-escalation` flag is explicitly rejected: global, unreviewable, records
no reason, and would pass a genuine downgrade.

## Scope

**In:**
- A decision on `inherit`, written down with the evidence that settled it.
- Implementation in `check_agent_templates.py`, plus the doc updates the change implies
  (`README.md`, `_shared/agent-templates/README.md`).
- Downgrades must still fail. An escalation mechanism that also permits pinning `scout`
  to a frontier model has inverted the point of the tool.
- Regression cases for whatever is built. The existing verification was hand-run and is
  listed in the PR #1 resolution comment; reuse it rather than reinventing.

**Out:**
- Editing the two consumer projects' agent files. Once a mechanism exists, whether their
  pins get annotated or reverted is the user's call, and those repos are private.
- Anything in `model-catalog.json` beyond reading `tier`. Catalog edits carry their own
  verification and evidence-grading obligations.
- The role model itself, the chief skills, and `check_catalog_sync.py`.
- Publishing, releasing, or version-tagging the repo.

## Precondition, not part of the design work

The live install at `~/.claude/skills/` is a separate clone that tracks `main` and is
pulled by hand. As of 2026-07-31 it sits at `863f55c`, four commits behind, so no
running session has the templates or the validator at all:

```bash
git -C ~/.claude/skills pull
```

Do that first, and confirm `~/.claude/skills/_shared/scripts/check_agent_templates.py`
exists afterwards. It is a precondition for testing against real installs, not a
deliverable.

## Suggested first session

1. Pull the live install (above). Confirm the validator is present.
2. Check `CLAUDE_CODE_SUBAGENT_MODEL`; if set, note its value — it changes what any
   `inherit` observation means.
3. Run the `inherit` experiment in Cursor. Record what it resolved to, per session model.
4. Write the decision into this doc, with the evidence.
5. Implement. Keep the failure messages in the existing voice: name the defect and its
   cost, never imply the defect is acceptable.
6. Re-run the full hand case set, plus the two consumer projects, which should now pass
   for the right reason rather than by loosening the check.

## Read these, not the whole repo

- `_shared/scripts/check_agent_templates.py` — the whole change lands here
- `_shared/model-catalog.json` — `role_hints`, `models.*.tier`, `tag_vocab.tier`
- `_shared/agent-templates/README.md` — the escalation allowance being formalized
- `fable-chief-agent/SKILL.md:58` — the escalation instruction that produces the drift
- `_shared/chief-agent-core.md` §Cost discipline — the policy the check enforces
- PR #1 (`73404ef`, `791226a`, `dbd0bab`) — why the validator works the way it does;
  the resolution comment lists the verification set

## Deliverable, and its negative

The deliverable is **a working change to the validator, gated on a written decision**.

It is *not* a design doc alone — do not stop at a recommendation. It is also not a
rewrite: if the answer turns out to be twelve lines in `allowed_models`, twelve lines is
the right answer. Route back to the user before adding a new file format, changing the
catalog, or touching anything in the Out list.

This doc is transient. Delete it when the work lands.
