---
description: Project standup — active tasks, blockers, and what's next for PAB Chiro
---

# Project Standup: PAB Chiro

Pull a quick standup view for the **PAB: Chiro Space** in ClickUp.

## What to do

1. Search ClickUp for all active tasks in the "PAB: Chiro Space" (workspace ID: `9017822495`, space ID: `90174262040`)
2. Group results by list (e.g. "v1.0.0 UAT", "Marketing")
3. Within each list, group by status ("in progress" first, then "not started" / "to do")

## Output format

Print a concise standup summary:

### In Progress
- List any tasks currently "in progress" — these are the active focus items

### Up Next
- List "not started" or "to do" tasks, limit to 5 most relevant per list
- If there are more, show the count (e.g. "+8 more in Marketing")

### Blockers
- Flag any tasks that are overdue or have comments indicating a blocker
- If none, say "No blockers"

## Rules
- Keep it short — this is a quick status check, not a full report
- Use plain text, no tables
- Include the ClickUp task URL for any in-progress items
- Do not modify any tasks — read only

## Save output
After printing the standup, also write it to a file named `YYYY-MM-DD-standup.md` (using today's date).
