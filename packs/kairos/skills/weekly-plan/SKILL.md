---
description: Start-of-week planning session to set priorities and goals.
---

# Weekly Plan

Start-of-week planning session. Every non-archived project should be moving toward completion or archive.

## Core Principle

With agentic workflows, the constraint isn't capacity - it's attention. You can run multiple agents in parallel. The question for each project is: "What attention does this get this week?"

**Sustainable pace is non-negotiable.** The system calculates recommended load based on trailing metrics. You can override, but it's logged. See [[load-calculation-spec]] for the math.

## Workflow

1. **Calculate load (FIRST)**

   Read trailing 7-14 days from daily notes:
   - `intensity` ratings (1-5)
   - `blocks` worked
   - `projects` touched

   Calculate:
   ```
   trailing_intensity = avg(intensity[]) over 7 days
   trailing_load = avg(blocks × project_count) over 7 days
   weeks_hot = consecutive weeks where avg_daily_load > 6
   ```

   Determine recommended load:
   ```
   IF illness_flag in last 7 days:
       recommended_daily = 3 (50% capacity)

   ELSE IF trailing_intensity >= 4.0:
       recommended_daily = 4 (70% capacity)

   ELSE IF weeks_hot >= 2:
       recommended_daily = 4 (70% capacity)

   ELSE IF trailing_intensity >= 3.5:
       recommended_daily = 5 (85% capacity)

   ELSE:
       recommended_daily = 6 (sustainable)
   ```

   Output the calculation visibly:
   ```
   ## Load Calculation

   Trailing 7 days:
   - Avg intensity: 4.2
   - Avg daily load: 9.3
   - Illness flag: yes (Wed-Fri)

   → Recommended daily load: 3 (recovery week)
   → Max blocks/day: 2
   → Max projects: 1-2
   ```

2. **Gather starting position**
   - Read `_data/projects/*.md` files to get ALL projects (exclude archived)
   - Read `_data/tasks/*.md` files to get professional one-off tasks
   - Get GitHub backlog counts for projects with repos:
     ```bash
     gh issue list --repo <owner/repo> --state open --json number --jq 'length'
     ```
   - Read last week's weekly summary for context

2. **Create or update weekly file**
   - File: `50-log/weekly/YYYY/YYYY-WNN.md`
   - Use template from `_templates/paz-weekly-plan.md`

3. **Fill Starting Position section**
   - Populate GitHub Backlog table with current open counts
   - Summarize last week's key outcomes under "Last Week"

4. **Project Triage - ALL non-archived projects**

   For each project, ask the appropriate question based on status:

   **Active (Tier 1):** "What's the commitment for [project]?"
   - Required weekly focus
   - Agent should be running on this

   **Active (Tier 2):** "Will [project] get touched this week?"
   - Encouraged but not required
   - Schedule agent time if yes

   **Paused:** "Why is [project] paused? Can we unblock or should we archive?"
   - Paused should be temporary, not permanent
   - Either find path to unblock or archive it
   - Consider: can an agent spike to investigate the blocker?

   **Concept:** "Should we start [project]? What's the first step?"
   - Define scope or archive
   - Consider: can an agent spike to define scope?

5. **Task Triage - Professional one-off tasks**

   Review `_data/tasks/*.md` for non-project tasks (courses, certifications, professional development):

   | Task | Status | This Week | Notes |
   |------|--------|-----------|-------|
   | iOS Course | in_progress | 1-2 hours | Learning |

   For each task:
   - **pending**: "Will this get attention this week?"
   - **in_progress**: "What's the next milestone?"
   - **completed**: Remove from triage (or archive the file)

6. **Add commitments**
   - Specific deliverables for the week
   - Reference GitHub issues if relevant (e.g., `chiro#130`)
   - Include task milestones if applicable

7. **Add notes**
   - Any context, constraints, or known calendar impacts

8. **Build daily schedules (respecting load calculation)**

   The load calculation determines blocks/day and project count. Build schedules accordingly:

   **Recovery (daily load ≤ 3):**
   ```
   8:00-10:00   Block 1 - Single project focus
   10:00-10:30  Transition - Piano or Yoga
   10:30-12:00  Optional Block 2 - Same project or rest
   12:00        Shutdown
   ```
   Max 2 blocks, 1-2 projects, early shutdown.

   **Steady (daily load 4-6):**
   ```
   8:00-10:00   Block 1 - Morning project
   10:00-10:30  Transition - Piano or Yoga
   10:30-12:30  Block 2 - Morning continued or secondary
   12:30-1:00   Lunch
   1:00-1:30    Admin (Mon-Fri only)
   1:30-3:30    Block 3 - Afternoon project
   3:30         Shutdown
   ```
   3 blocks, 2 projects, normal shutdown.

   **Heavy (daily load > 6) - time-limited, max 2 weeks:**
   ```
   8:00-10:00   Block 1 - Morning project (usually Chiro)
   10:00-10:30  Transition - Piano or Yoga
   10:30-12:30  Block 2 - Morning project continued or secondary
   12:30-1:00   Lunch
   1:00-1:30    Admin (Mon-Fri only)
   1:30-3:30    Block 3 - Afternoon project (usually Resin)
   3:30-4:00    Transition - Piano or Yoga
   4:00-5:00    Block 4 - Flex/other projects
   5:00         Shutdown
   ```
   4 blocks, 2-3 projects, full day.

   - Adjust for calendar conflicts (meetings, appointments)
   - Assign projects to blocks based on triage AND load limits

9. **Generate ICS file for Apple Calendar**
   - Create `50-log/weekly/YYYY/WNN-time-blocks.ics`
   - Include all coding blocks, transitions (piano/yoga), and admin slots
   - User double-clicks to import into Apple Calendar for notifications
   - ICS format:
     ```
     BEGIN:VCALENDAR
     VERSION:2.0
     PRODID:-//WNN Time Blocks//EN

     BEGIN:VEVENT
     DTSTART:YYYYMMDDTHHMMSS
     DTEND:YYYYMMDDTHHMMSS
     SUMMARY:Block 1: Chiro
     DESCRIPTION:Deep work - 3 pomos
     END:VEVENT
     ...
     END:VCALENDAR
     ```

10. **Confirm**
   - Summarize the week's project attention
   - Point to ICS file for calendar import
   - Ready to start

## Output Format

Write to `50-log/weekly/YYYY/YYYY-WNN.md`:

```markdown
---
tags: [weekly, planner]
week: YYYY-WNN
---

# Starting Position

> Generated by /weekly-plan

## GitHub Backlog

| Project | Open | Link |
|---------|------|------|
| chiro | 23 | [issues](https://github.com/mpazaryna/chiro/issues) |
| systemata | 2 | [issues](https://github.com/mpazaryna/systemata/issues) |

## Last Week

- Chiro: Glass UI shipped
- Resin: Waiting on API keys

---

# Project Triage

> Every non-archived project should be moving toward completion or archive

| Project | Status | This Week | Notes |
|---------|--------|-----------|-------|
| Chiro | active | MLX testing | Tier 1 - agent running |
| Resin | active | Blocked on API keys | Tier 1 - waiting |
| Dailyframe | active | Skip this week | Tier 1 - deprioritized |
| Systemata | active | Issue #18 | Tier 2 |
| Yellow House | paused | Spike to define scope | Unblocking |
| Authentic Advantage | paused | Archive decision | Needs decision |
| Productivity MCP | concept | Skip | Not ready |

# Commitments

- Chiro: Complete MLX testing (chiro#130)
- Systemata: Close issue #18
- Yellow House: Agent spike to define project scope

# Notes

Heavy Chiro week. Resin blocked externally.
```

## Project Status Reference

| Status | Question | Action |
|--------|----------|--------|
| active (tier 1) | What's the commitment? | Agent runs on this |
| active (tier 2) | Will it get touched? | Schedule agent if yes |
| paused | Why paused? Unblock or archive? | Spike or decide |
| concept | Start or archive? | Define scope or drop |
| archived | — | Don't include |

## Load-Based Scheduling

The load calculation drives the schedule. No more assuming every week is heavy.

| Daily Load | Blocks | Projects | Shutdown |
|------------|--------|----------|----------|
| ≤ 3 (recovery) | 1-2 | 1-2 | 12:00 |
| 4-6 (steady) | 3 | 2 | 3:30 |
| > 6 (heavy) | 4 | 2-3 | 5:00 |

**Constraints:**
- Heavy is time-limited: max 2 consecutive weeks
- After 2 heavy weeks, next week must be steady or recovery
- Illness flag forces recovery regardless of other metrics

**Sustainable thresholds (calibrate over time):**
| Metric | Sustainable | Warning | Reduce |
|--------|-------------|---------|--------|
| daily_load | ≤ 6 | 7-8 | ≥ 9 |
| trailing_intensity | ≤ 3.0 | 3.5-4.0 | ≥ 4.0 |
| weeks_above_sustainable | 0-1 | 2 | ≥ 3 |

- **Sunday:** Rest day, no coding
- **Saturday:** Coding but no admin
- **Pomodoro:** 30 min work / 10 min break, 3 pomos per 2h block

## Notes

- No project should be in limbo indefinitely
- Paused means "temporarily deprioritized" not "forgotten"
- Every week, paused/concept projects get the question: "Move forward or archive?"
- Agents can spike on blockers - use them
- Run `/kickoff` daily to stay oriented
- Run `/weekly-summary` at end of week to close the loop
- ICS file goes to `50-log/weekly/YYYY/WNN-time-blocks.ics` - double-click to import to Apple Calendar

## Proactive Prescription

**The system prescribes, it doesn't ask.**

When you run `/weekly-plan`, lead with the load calculation. Don't ask "what pace do you want?" - tell the user what the data says. They can override, but the default is data-driven.

```
## Load Calculation

Your trailing 7-day intensity is 4.2 with avg daily load of 9.3.
You had an illness flag Wed-Fri.

This week is a recovery week: 2 blocks/day, 1-2 projects max.

[Continue with project triage within those constraints]
```

## Doc Maintenance

After each weekly cycle, update [[load-calculation-spec]] if:

1. **Threshold calibration needed** - Observed sustainable load differs from defaults
2. **Pattern discovered** - e.g., "illness follows 2+ heavy weeks"
3. **Override outcome** - Did pushing through work or backfire?

The spec is a living document. The system maintains it, not just references it.
