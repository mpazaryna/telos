---
description: Generate monthly retrospective from daily notes.
---

# Monthly Summary

Reads all daily notes for the current month and generates an in-depth retrospective.

## Workflow

1. **Determine current month**
   - Get today's date
   - Monthly file: `50-log/monthly/YYYY/YYYY-MM.md`
   - Create folder if needed

2. **Read all daily notes for the month**
   - Find all daily notes from the 1st through today (or end of month)
   - Read each one completely - Focus, Log, Shutdown sections
   - Note which days have notes and which are missing

3. **Analyze and synthesize**

   Generate deeper analysis than weekly:

   **Month overview**
   - How many days had notes?
   - General rhythm and consistency

   **Project progress**
   - For each project in `_data/`:
     - How many days of focus?
     - What was accomplished?
     - Current status vs start of month

   **Tier 1 accountability**
   - Week-by-week: did Chiro get focus?
   - Week-by-week: did Resin get focus?
   - Overall tier 1 coverage percentage

   **Themes and patterns**
   - What topics/projects dominated?
   - What got neglected?
   - Recurring blockers across weeks
   - Energy patterns (if observable)

   **Wins**
   - Significant accomplishments
   - Milestones reached
   - Problems solved

   **Gaps**
   - What was intended but didn't happen?
   - Persistent carry-overs that never resolved
   - Projects that stalled

   **Insights**
   - What did you learn?
   - What surprised you?
   - What would you do differently?

   **Next month**
   - Based on patterns, what should next month focus on?
   - Any course corrections needed?

4. **Write monthly file**
   - Create or overwrite `50-log/monthly/YYYY/YYYY-MM.md`
   - Full file, not appended

## Output Format

Write to `50-log/monthly/YYYY/YYYY-MM.md`:

```markdown
---
tags: [monthly, retrospective]
date: YYYY-MM
---

# Monthly Summary - YYYY-MM

*Generated: YYYY-MM-DD HH:MM*

## Overview

[X days with notes out of Y days in month]
[General rhythm observations]

## Project Progress

### Chiro (Tier 1)
- Days of focus: X
- Accomplishments: [list]
- Status: [current state]

### Resin (Tier 1)
- Days of focus: X
- Accomplishments: [list]
- Status: [current state]

### [Other projects as relevant]

## Tier 1 Accountability

| Week | Chiro | Resin |
|------|-------|-------|
| W01  | Y/N   | Y/N   |
| W02  | Y/N   | Y/N   |
| ...  | ...   | ...   |

## Themes

[What dominated the month, what patterns emerged]

## Wins

- [significant accomplishments]

## Gaps

- [what didn't happen, persistent blockers]

## Insights

[learnings, surprises, reflections]

## Next Month

[suggested focus, course corrections]
```

## Notes

- Can be run multiple times - overwrites entire file
- Reads raw daily notes, provides independent analysis
- More reflective than weekly - look for larger patterns
- Be honest about gaps - that's the value
- Create `50-log/monthly/YYYY/` folder if it doesn't exist
