---
description: Quick morning orientation. Surface what matters, set focus.
---

# Kickoff

Quick morning orientation - under 2 minutes. Synthesize, don't list.

## Determine Today's Date

First, establish today's date from the system environment (provided as "Today's date: YYYY-MM-DD"). Use this to:
- Calculate yesterday's date for reading the previous daily note
- Determine the day of week (Saturday = end of week)
- Calculate the ISO week number for the weekly file

## Gather Context (silently)

Read these in parallel, don't output yet:
1. Yesterday's daily note - find Shutdown section (Tomorrow, Carry-over)
2. `_data/projects/` folder - scan for tier-1 and tier-2 projects
3. `_data/tasks/` folder - scan for pending/in_progress professional tasks
4. This week's weekly note (`50-log/weekly/YYYY/YYYY-WNN.md`)
5. Recent daily notes - check which tier-1 projects have had focus this week

## Present Summary

Output a single concise block. Only include sections that have content.

```
## Kickoff - YYYY-MM-DD (DayName)

[Yesterday's "Tomorrow" item if present]
[Calendar items for today if any]
[Tier 1 alert if chiro or resin haven't had focus this week]
[Persistent blockers if same item 3+ days]

What's your focus today?
```

### What to Flag

- **Tier 1 gaps**: "Chiro hasn't had focus yet this week" (it's Thursday)
- **Persistent carry-over**: "Chiro backlog - day 4" not just "Carry-over: Chiro backlog"
- **Calendar conflicts**: Only if something scheduled might affect focus choice
- **In-progress tasks**: Surface any `_data/tasks/` with `status: in_progress` (e.g., "iOS course in progress")

### What to Skip

- Inbox counts (not actionable in kickoff)
- Empty calendar days
- Weekly progress fractions ("2 of 5 complete")
- Projects without issues

## Ask Focus

Simple open question: "What's your focus today?"

Don't use AskUserQuestion with predefined options. Let the user type freely.

## Create/Update Daily Note

After user responds:
1. Create today's daily note if it doesn't exist (use template pattern from recent notes)
2. Set the Focus section
3. Add From Yesterday context

## Example Output

```
## Kickoff - 2026-01-16 (Thursday)

Yesterday you planned: Systemata #18
Chiro hasn't had focus yet this week.
No meetings today.

What's your focus today?
```

Short. Synthesized. Actionable.

## Tier Reference

Read from `_data/` frontmatter:
- **Tier 1** (weekly required): Check if touched this week, flag if not
- **Tier 2** (weekly encouraged): Gentle nudge if dormant 2+ weeks
- **Active/Paused**: Don't mention unless user asks

## Principles

- **Synthesize, don't list** - "Chiro (day 4)" not "Carry-over: Chiro backlog"
- **Skip what's empty** - No calendar? Don't mention it
- **Be conversational** - No forced multiple choice
- **Quick by default** - Expand only if asked
- **Flag patterns** - Recurring blockers, tier 1 gaps
