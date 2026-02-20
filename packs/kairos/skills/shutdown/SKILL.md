---
description: End-of-day capture. Quick closure, clear state.
---

# Shutdown

Quick end-of-day ritual - under 3 minutes. Capture and clear.

## Gather Context (silently)

Read in parallel, don't output yet:
1. Today's daily note - what was the Focus?
2. `_data/` folder - all non-archived projects
3. Active project repos - check for uncommitted work
4. Day of week - Friday triggers week review

## Check Uncommitted Work

Run `git status` in repos for tier-1 and active projects. Only surface if there are uncommitted changes.

If found: "resin-platform has uncommitted changes - commit, stash, or leave?"

Don't use AskUserQuestion. Just ask and wait for response.

## Ask Core Questions

Simple, conversational. No predefined options.

```
What did you accomplish today?
Any blockers or carry-over?
Any project status changes? (unblocked, stalled, ready to archive?)
What's first tomorrow?
```

Wait for responses, then record.

## Capture Load Metrics

After the core questions, capture the load metrics for the planning system:

```
Quick metrics for the week:
- Intensity today? (1-5, where 1=coasting, 3=steady, 5=full burn)
- How many blocks did you actually work?
- Which projects got attention?
```

These feed the load calculation that determines next week's pace. See [[load-calculation-spec]] for details.

## Record to Daily Note

Update the Shutdown section AND the frontmatter:

**Frontmatter additions:**
```yaml
---
tags: [daily]
date: 2026-01-20
intensity: 4
blocks: 3
projects: [chiro, resin]
---
```

**Shutdown section:**
```markdown
## Shutdown

**Accomplished:**
- [from response]

**Carry-over:**
- [from response, or "None"]

**Project Changes:**
- [any status changes, or omit if none]

**Tomorrow:**
- [from response]

**Load:** intensity 4 · 3 blocks · chiro, resin
```

## Friday: Week Check

On Fridays, after the daily questions, add:

```
It's Friday. Quick project review:

Active:
- Did Chiro move forward?
- Did Resin move forward?
- Did Systemata move forward?

Paused/Concept:
- Yellow House - still paused or ready to unblock/archive?
- Authentic Advantage - still paused or ready to unblock/archive?
- Productivity MCP - define scope or archive?

Any project status changes for next week?
```

Capture answers in the daily note. Suggest running `/weekly-summary` for the full retrospective.

## Confirm and Close

Brief summary of what was captured:

```
Recorded. Uncommitted work handled. See you tomorrow.
```

Or on Friday:
```
Week captured. Run /weekly-summary for full retrospective. See you Monday.
```

## Example Output

```
## Shutdown - 2026-01-16

resin-platform has 1 uncommitted file (CONTENT-SERIES-PROPOSAL.md)
Commit, stash, or leave?

> commit

Committed.

What did you accomplish today?
> Systemata #18, planning session for kickoff improvements

Any blockers or carry-over?
> Chiro backlog still pending

Any project status changes?
> Yellow House - decided to archive, not worth continuing

What's first tomorrow?
> Chiro focus day

Recorded. See you tomorrow.
```

## Principles

- **Quick capture** - Don't overthink, just record
- **Uncommitted code is a smell** - Surface it, let user decide
- **Conversational** - No forced choices or multi-select
- **Project status changes matter** - Capture when things unblock, stall, or archive
- **Friday covers ALL projects** - Not just tier-1, everything non-archived
- **Closure over documentation** - The goal is to clear your head
