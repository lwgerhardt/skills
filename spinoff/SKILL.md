---
name: spinoff
description: Hand a workstream off to a fresh agent session. Use when work is worth doing but does not belong in the current conversation — a design pass, an investigation, an adjacent feature, a follow-up someone else should own. Writes a committed handoff doc, then queues a task chip that starts its own session pointing at it. Triggers on "hand this off", "spin this off", "give me something to hand to a new agent", "queue this for later", "someone should look into X".
---

# Spin-off handoff

Turn something worth doing into a self-contained handoff a fresh agent can pick up cold.

Portable: this skill hardcodes no repo's layout or policy. Step 1 discovers them.

## The one constraint that shapes everything

**Conversation history does not cross the boundary. Repo state does.**

The spun-off session starts clean, typically in its own worktree. It sees the project's ambient context — agent instructions, rules, memory — and the repo. It sees nothing of the conversation that produced the handoff.

Two consequences, and most bad handoffs violate one:

1. **Durable reasoning goes in the committed doc**, never only in the chip prompt. A chip can be dismissed, is not versioned, is not reviewable, and cannot be found later. Everything you learned belongs in a file.
2. **Commit the doc before queuing the chip.** A fresh worktree is built from the repo — an uncommitted doc is not in it. This is a correctness requirement, not tidiness.

Never write "as discussed above", "the approach we settled on", or anything else that assumes the current conversation.

## Steps

### 1. Adapt to the project first

Do not assume any layout. Establish, cheaply:

- **Where design and planning docs live.** Look for existing `*-handoff.md`, `*-design.md`, or a `planned/` or `rfc/` directory, and match whatever is already there — path, filename shape, and section conventions.
- **Required doc metadata.** Some repos gate doc format in pre-commit or CI (a status line, a date, an owner). Check `.pre-commit-config.yaml` and the repo's agent instructions. A handoff that fails the commit hook wastes a cycle.
- **Commit and push policy.** Read `CLAUDE.md` / `AGENTS.md` / contributing docs. Many repos allow doc-only commits to land directly but require code to go through review. Follow what you find; ask if it is genuinely unclear.
- **Any constraint on spending.** CI minutes, cloud budget, rate limits. If one is tight, the spun-off agent needs to know before it opens a PR.

Carry the answers into the doc and the chip prompt. Everything below is written in terms of what you find here.

### 2. Establish scope

Get the job into one line. Then get the **out**-of-scope list, which matters as much: adjacent work that is blocked, tempting, or already settled elsewhere. An agent that absorbs a neighbouring blocked task delivers nothing.

If the ask is ambiguous in a way that changes the deliverable, ask the user once. Do not hand ambiguity downstream — the receiving agent has less context than you, not more.

### 3. Recon, and delegate it

Send a read-only scout, pinned to a cheap model, to map what already exists. A handoff built on guesses is worse than none, because the receiving agent trusts it.

Require **file:line references** and **explicit negatives**. Instruct the scout to say "DOES NOT EXIST" plainly where that is the answer — a confident negative saves the next agent a fruitless search and is often the most valuable line in the doc.

Sanity-check anything the handoff's shape depends on yourself. Scout findings are inputs, not verified facts.

### 4. Separate unknowns from details

Unknowns that change the **shape** of the work go at the top of the doc, each with a **concrete experiment** — not a description of the uncertainty. Where the project's stack diverges from upstream defaults, say "confirm this empirically; do not take it from the docs."

An unknown that only changes details is not load-bearing. Do not inflate the list.

### 5. Write the doc

Match the project's conventions from step 1. Content, in this order:

- **Status** — nothing started, and what the first session is expected to produce. Include whatever metadata the repo's hooks require.
- **The job**, in one line, plus why it is being handed off now.
- **What exists today (verified `<date>`)** — a table with file:line and explicit DOES NOT EXIST rows.
- **Load-bearing unknowns**, each with its experiment.
- **Scope**, in and explicitly out.
- **Suggested first session** — a short ordered list.
- **Read these, not the whole repo** — a curated path list, so the new agent does not burn its context rediscovering what you already mapped.

Name the deliverable **and its negative**. If the topic sounds like code, say "the deliverable is a design doc, not an implementation" explicitly — an agent handed a feature name will start writing the feature.

Cross-link from any existing doc this supersedes or continues, so the trail is followable from either end.

### 6. Verify, then commit

Check every link resolves before committing — a handoff with dead links reads as untrustworthy:

```bash
for f in <each path referenced>; do [ -e "$f" ] && echo "OK $f" || echo "MISS $f"; done
```

Then commit per the policy found in step 1.

### 7. Queue the chip

Use the host's background-task tool (in Claude Code, `mcp__ccd_session__spawn_task`) with `cwd` set to the repo.

- `title` — imperative, under 60 chars.
- `tldr` — 1–2 sentences, plain English, no file paths. This is the tooltip the user reads.
- `prompt` — opens with **"Start by reading `<the doc>`"**, then restates only what is most likely to be skimmed past:
  - the deliverable and its negative
  - the experiments to run *before* drafting
  - the out-of-scope list
  - which decisions route back to the user rather than being the agent's to make
  - working agreements it cannot infer: commit policy, budget constraints, anything the user does personally

The prompt is a second layer of defence, not a second copy of the doc. If the prompt is doing the doc's job, the doc is too thin.

Check whether a chip for this already exists before creating one — duplicates are noise. Dismiss superseded chips, creating the replacement first.

**If the host has no chip mechanism**, stop after the commit and tell the user the doc is ready and how to start a session against it. The doc is the deliverable; the chip is convenience.

### 8. Tell the user what crossed the boundary

Say what is in the doc, what is in the prompt, and that anything they think of later must go into the doc or be said directly to the running session — telling *you* will not reach it.

## Model selection

Two different questions, and only one of them is out of reach.

**The session's own model is the host's.** The spawn tool takes no model parameter, and a session cannot switch itself — model selection is host/UI-level, not agent-invocable. Do not write "switch to <model> first" into a chip prompt; it cannot be obeyed.

**The model that does the work is yours to control**, per task rather than per session, through subagent pins. A session on a cheap default can still route a hard slice to a role pinned to a frontier model, and a session on an expensive default can push recon down to a cheap one. Since repo state crosses the boundary and conversation does not, **the durable place for this is the project's agent definitions** (`.claude/agents/*.md` frontmatter), not the chip prompt. Where those already exist, the chip prompt only needs to name the routing — "delegate the synthesis to `executor`, recon to `scout`" — and the pins do the rest, whatever the session is running on.

Where they do not exist, the prompt can set `model` explicitly on each delegation instead.

Check `CLAUDE_CODE_SUBAGENT_MODEL` before relying on any of it: as an environment variable it **silently overrides frontmatter pins**, and it is the first thing to look at when a role appears to be running on the wrong model.

If the *session's own* reasoning tier genuinely matters — not merely a slice you could delegate — that is a human decision. Say so plainly and let the user set it; do not imply control you lack.

## Failure modes

| Symptom | Cause |
|---|---|
| New agent re-derives what you already knew | Reasoning left in the conversation instead of the doc |
| New agent starts implementing | Deliverable's negative never stated |
| New agent's design is invalidated on day two | A load-bearing unknown was described rather than settled by experiment |
| New agent absorbs a blocked neighbouring task | No explicit out-of-scope list |
| New session cannot find the doc | Chip queued before the doc was committed |
| Commit rejected by a hook | Step 1 skipped — repo gates doc format |
| New agent burns budget or forks a dependency | A decision that was the user's was never routed back |
