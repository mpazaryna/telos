---
name: apple-calendar
description: Apple Calendar.app integration for macOS. CRUD operations for events, search, and multi-calendar support.
metadata: {"clawdbot":{"emoji":"📅","os":["darwin"]}}
---

# Apple Calendar

Interact with Calendar.app via AppleScript.

## How to execute

You are running on macOS with full access to Calendar.app via AppleScript. Use the `run_command` tool to execute the shell scripts listed below. Interpret the user's request, pick the right script and arguments, run it, and present the output in a clean readable format. Always run the scripts — never just explain them.

## Commands

| Command | Usage |
|---------|-------|
| List calendars | `scripts/cal-list.sh` |
| Read event | `scripts/cal-read.sh <event-uid> [calendar_name]` |
| Create event | `scripts/cal-create.sh <calendar> <summary> <start> <end> [location] [description] [allday] [recurrence]` |

## Date Format

- Timed: `YYYY-MM-DD HH:MM`
- All-day: `YYYY-MM-DD`

## Recurrence

| Pattern | RRULE |
|---------|-------|
| Daily 10x | `FREQ=DAILY;COUNT=10` |
| Weekly M/W/F | `FREQ=WEEKLY;BYDAY=MO,WE,FR` |
| Monthly 15th | `FREQ=MONTHLY;BYMONTHDAY=15` |

## Output

- List: `CalendarName | writable` or `CalendarName | read-only`
- Read: UID, Calendar, Summary, Start, End, All Day, Location, Description, URL, Recurrence
- Create: returns the UID of the created event

## Notes

- Read-only calendars (Birthdays, Holidays) can't be modified
- Calendar names are case-sensitive
- Only use the three scripts listed above — other scripts in the directory are broken
