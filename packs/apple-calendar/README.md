# Apple Calendar Agent Pack

A telos agent pack for macOS Calendar.app integration — list calendars, read events, and create new events via AppleScript. Ported from the OpenClaw skill ecosystem.

## What's in the pack

```
packs/apple-calendar/
  agent.toml       # agent metadata (name, description, working_dir)
  scripts/
    cal-list.sh    # list all calendars
    cal-read.sh    # read a specific event by UID
    cal-create.sh  # create a new calendar event
  skills/
    calendar/
      SKILL.md     # skill prompt: natural language → script execution
```

### How it works

The calendar skill interprets natural language requests and executes the appropriate AppleScript-based shell script via the `run_command` built-in tool. The scripts interact directly with Calendar.app on macOS.

**Working scripts:** `cal-list.sh`, `cal-read.sh`, `cal-create.sh`

**Known broken scripts:** `cal-events.sh`, `cal-search.sh`, `cal-update.sh`, `cal-delete.sh` — these hang due to an upstream AppleScript bug. They are included in the pack but the SKILL.md instructs the model to only use the three working scripts.

## Prerequisites

1. **macOS** — Calendar.app is required (this pack is darwin-only)
2. **telos** installed (`uv pip install -e .` from the repo root)
3. **ANTHROPIC_API_KEY** in `~/.config/telos/.env` (or use Ollama with `TELOS_PROVIDER=ollama`)
4. **Calendar.app permissions** — you may need to grant terminal/automation access in System Settings > Privacy & Security

## Install

```bash
telos install packs/apple-calendar
```

Verify:

```bash
telos agents          # should show "apple-calendar" in the table
telos list-skills     # should show "calendar"
```

## Usage

### List calendars

```bash
telos --agent apple-calendar "list my calendars"
```

Shows all calendars with their writable/read-only status.

### Read an event

```bash
telos --agent apple-calendar "read event ABC-123-DEF"
```

Retrieves full event details: UID, calendar, summary, start/end, location, description, recurrence.

### Create an event

```bash
telos --agent apple-calendar "create a meeting tomorrow at 2pm to 3pm called Team Sync on Work calendar"
```

Creates the event and returns its UID. Supports:
- Timed events: `YYYY-MM-DD HH:MM` format
- All-day events: `YYYY-MM-DD` format
- Location and description
- Recurrence rules (daily, weekly, monthly via RRULE syntax)

### Dry run

```bash
telos --dry-run --agent apple-calendar "list calendars"
```

Routes the request and prints the matched skill without executing.

## Scripts reference

| Script | Arguments | Description |
|--------|-----------|-------------|
| `cal-list.sh` | _(none)_ | List all calendars with writable status |
| `cal-read.sh` | `<event-uid> [calendar_name]` | Read event details by UID |
| `cal-create.sh` | `<calendar> <summary> <start> <end> [location] [description] [allday] [recurrence]` | Create a new event |

## Recurrence patterns

| Pattern | RRULE |
|---------|-------|
| Daily 10 times | `FREQ=DAILY;COUNT=10` |
| Weekly Mon/Wed/Fri | `FREQ=WEEKLY;BYDAY=MO,WE,FR` |
| Monthly on the 15th | `FREQ=MONTHLY;BYMONTHDAY=15` |

## Notes

- Read-only calendars (Birthdays, Holidays) cannot be modified
- Calendar names are case-sensitive
- This pack was ported from OpenClaw — the SKILL.md uses `run_command` to execute scripts since telos doesn't have a native bash tool

## Uninstall

```bash
telos uninstall apple-calendar
```
