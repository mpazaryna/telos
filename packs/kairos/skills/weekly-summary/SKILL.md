---
description: Generate weekly retrospective from daily notes.
---

# Weekly Summary

Reads all daily notes for the current week and generates an in-depth retrospective. Tracks ALL non-archived projects.

## Core Principle

Every non-archived project should be moving toward completion or archive. The weekly summary evaluates: did each project move forward, stay stuck, or get archived?

## Workflow

1. **Determine current week**
   - Get today's date and calculate ISO week number
   - Week runs Sunday through Saturday
   - Weekly file: `50-log/weekly/YYYY/YYYY-WNN.md`

2. **Read all daily notes for the week**
   - Find daily notes from Sunday through Saturday of current week
   - Read each one completely - Focus, Log, Shutdown sections
   - Note which days have notes and which are missing

3. **Read ALL project status**
   - Read `_data/*.md` files to get ALL projects
   - Track: active (tier 1, tier 2), paused, concept
   - Exclude only archived

4. **Gather GitHub metrics**
   - For each project with a `repo:` property, call:
     ```bash
     gh issue list --repo <owner/repo> --state open --json number --jq 'length'
     gh issue list --repo <owner/repo> --state closed --json closedAt --jq '[.[] | select(.closedAt > "<week-start>")] | length'
     gh issue list --repo <owner/repo> --state all --json createdAt --jq '[.[] | select(.createdAt > "<week-start>")] | length'
     ```
   - Calculate net change (opened - closed)

5. **Analyze ALL projects**

   For each non-archived project, evaluate:

   **Active projects:**
   - Did it get focused attention?
   - What was accomplished?
   - Backlog movement (issues opened/closed)

   **Paused projects:**
   - Did the blocker get addressed?
   - Should it stay paused, unblock, or archive?
   - Was there any spike/investigation?

   **Concept projects:**
   - Was scope defined?
   - Should it start, stay concept, or archive?

6. **Synthesize patterns**

   **Accomplishments**
   - What was completed across the week?
   - Pull from Shutdown "Accomplished" sections

   **Project Movement**
   - Which projects moved forward?
   - Which stayed stuck?
   - Any status changes (paused → active, concept → archived, etc.)?

   **Blockers and Decisions Needed**
   - What's blocking paused projects?
   - What decisions are pending?

   **Observations**
   - What worked well?
   - What didn't work?

7. **Write to weekly file**
   - Append (or replace) a `# Weekly Summary` section at the bottom
   - If section already exists, replace it entirely
   - Include generation timestamp

## Output Format

Append to `50-log/weekly/YYYY/YYYY-WNN.md`:

```markdown
---

# Weekly Summary

*Generated: YYYY-MM-DD HH:MM*

## Accomplishments
- [synthesized from daily notes]

## Project Status

| Project | Status | Movement | Next |
|---------|--------|----------|------|
| Chiro | active | Forward - Glass UI shipped | MLX testing |
| Resin | active | Blocked - waiting on API keys | Follow up |
| Dailyframe | active | No movement | Needs attention |
| Systemata | active | Forward - #18 in progress | Complete #18 |
| Yellow House | paused | No movement | Spike or archive? |
| Authentic Advantage | paused | No movement | Decision needed |
| Productivity MCP | concept | No movement | Define or archive? |

## Active Projects
- **Chiro:** [what happened, what's next]
- **Resin:** [what happened, what's next]
- **Systemata:** [what happened, what's next]

## Paused/Concept Review
- **Yellow House:** Still paused. Blocker: [X]. Action: [spike/archive/unblock]
- **Authentic Advantage:** Still paused. Blocker: [X]. Action: [spike/archive/unblock]
- **Productivity MCP:** Still concept. Action: [define scope/archive]

## Patterns
**What moved forward:**
- [projects that progressed]

**What stayed stuck:**
- [projects with no movement - why?]

**Blockers:**
- [external blockers, decisions needed]

## Observations
[what worked, what didn't, insights]

## Next Week
[suggested focus based on patterns]

## GitHub Activity

*Metrics as of YYYY-MM-DD*

| Project | Open | Closed | Opened | Net |
|---------|------|--------|--------|-----|
| [project](url) | N | N | N | +/-N |
```

## Project Movement Categories

| Movement | Meaning |
|----------|---------|
| Forward | Made progress, issues closed, work shipped |
| Blocked | Waiting on external input |
| No movement | Didn't get attention (why?) |
| Status change | Moved between active/paused/concept/archived |

## Notes

- Can be run multiple times - overwrites previous summary
- Track ALL non-archived projects, not just active
- Be honest about stuck projects - they need attention or archiving
- Paused projects should have a clear blocker and unblock path
- Concept projects should either start or archive - no indefinite limbo
