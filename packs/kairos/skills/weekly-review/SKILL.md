---
description: Weekly review of progress and planning for the week ahead.
---

# Weekly Review

A consolidated view of the past week to support planning the next.

## Workflow

1. **Determine the week**
   - Use system date to identify current week (YYYY-WNN)
   - Find or create weekly note at `50-log/weekly/YYYY/YYYY-WNN.md`

2. **Check for timesheet (REQUIRED)**
   - Look for `50-log/weekly/YYYY/YYYY-WNN-timesheet.pdf` (Clockify export)
   - **STOP if not found.** Tell the user:
     - Expected file: `50-log/weekly/YYYY/YYYY-WNN-timesheet.pdf`
     - Action: Export Clockify summary report for the week and save it with this name
   - Timesheet data is ground truth - no review without it

3. **Review daily notes and interstitials**
   - Read daily notes from `50-log/daily/YYYY/` for the past 7 days
   - Read interstitial captures from `50-log/interstitial/` for the week
   - Extract accomplishments from Shutdown sections
   - Note any carry-over items

4. **Present summary**
   - Time breakdown by project (from timesheet if available)
   - What was accomplished (from daily notes + interstitials)
   - What was carried over
   - Patterns or observations (reconcile timesheet vs. daily notes narrative)

5. **Ask for focus**
   - "What do you want to focus on this week?"
   - Can be projects, areas, or themes

6. **Record in weekly note**
   - Write focus areas and goals to weekly note
   - Optionally add calendar items for each day

## Example Output

```
## Weekly Review - 2026-W03

### Time Breakdown (from timesheet)
Total: 36h 15m

| Project | Hours | % |
|---------|-------|---|
| Chiro (SOAP Notes) | 23:22 | 64% |
| Admin/Internal | 12:08 | 33% |
| Resin | 0:45 | 2% |

Top tasks:
- Transfer data between mac and iOS: 14:46 (41%)
- Obsidian/Systemata refactors: 12:08 (33%)
- Chiro UI work: 8:36 (24%)

### Accomplishments
- Cairo spike delivered - local syncing working both ways
- Vault cleanup - stalled projects triaged to paused/archived
- Claude skills integration (markdown, bases, json-canvas)
- Resin billing completed

### Carried Over
- Systemata #18

### Patterns
- Thursday was the breakthrough day (19h push)
- Chiro dominated the week at 64% of time

### This Week
What do you want to focus on this week?
> [user input]

Recording to 50-log/weekly/2026-W03.md...
```

## Notes

- Keep it brief - 10 minutes max
- Focus on patterns, not exhaustive lists
- This is for planning, not historical analysis
- For GitHub-specific project tracking, use Systemata
- Timesheet naming: `YYYY-WNN-timesheet.pdf` (e.g., `2026-W03-timesheet.pdf`)
- Timesheet is ground truth - daily notes capture narrative, timesheet captures reality
