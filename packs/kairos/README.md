# Kairos Agent Pack

A telos agent pack for personal productivity — daily rituals, weekly/monthly retrospectives, and load-based planning. Ships 7 skills that operate on an Obsidian vault.

## What's in the pack

```
packs/kairos/
  agent.toml       # agent metadata (name, description, executor)
  skills/
    kickoff/
      SKILL.md     # morning orientation — surface what matters, set focus
    shutdown/
      SKILL.md     # end-of-day capture — quick closure, clear state
    interstitial/
      SKILL.md     # timestamped note capture throughout the day
    weekly-plan/
      SKILL.md     # start-of-week planning with load calculation
    weekly-review/
      SKILL.md     # weekly progress review against Clockify timesheet
    weekly-summary/
      SKILL.md     # weekly retrospective from daily notes
    monthly-summary/
      SKILL.md     # monthly retrospective with project accountability
```

### How it works

Kairos skills read and write files in an Obsidian vault. When telos installs this pack, it:

1. Copies `skills/*/SKILL.md` to `~/.local/share/telos/agents/kairos/skills/`
2. Registers the agent in `~/.config/telos/agents.toml`
3. Sets `working_dir` to `~/obsidian` — Claude Code runs in the vault directory

At execution time, telos routes natural language to a skill and spawns Claude Code with the skill prompt. Claude reads and writes vault files (daily notes, weekly plans, interstitials) directly.

### Vault structure expected

Kairos expects an Obsidian vault with this layout:

```
~/obsidian/
  _data/
    projects/      # project records with tier/status frontmatter
    tasks/         # professional one-off tasks
  50-log/
    daily/         # daily notes (YYYY/YYYY-MM-DD.md)
    weekly/        # weekly plans and summaries (YYYY/YYYY-WNN.md)
    monthly/       # monthly retrospectives (YYYY/YYYY-MM.md)
    interstitial/  # timestamped captures (YYYY-MM-DD-HHMMSS.md)
```

See the [kairos repo](https://github.com/mpazaryna/kairos) for the full vault conventions and system spec.

## Prerequisites

1. **Claude Code** installed and on your PATH (`npm install -g @anthropic-ai/claude-code`)
2. **telos** installed (`uv pip install -e .` from the repo root)
3. **Obsidian vault** at `~/obsidian` (or update `working_dir` in `agents.toml` after install)
4. **ANTHROPIC_API_KEY** in `~/.config/telos/.env` (needed for API-based routing)

## Install

```bash
telos install packs/kairos
```

If your vault is not at `~/obsidian`, update the working directory:

```bash
# Edit ~/.config/telos/agents.toml
# Change working_dir under [agents.kairos] to your vault path
```

Verify:

```bash
telos agents               # should show "kairos" in the table
telos list-skills           # should show all 7 skills
```

## Usage

### Dry run (no execution)

```bash
telos --dry-run "kickoff"
```

This routes the request and prints the matched skill without invoking Claude Code.

### Live run

```bash
telos "kickoff"                # morning orientation
telos "shutdown"               # end-of-day capture
telos "interstitial"           # quick note capture
telos "weekly-plan"            # start-of-week planning
telos "weekly-review"          # review against timesheet
telos "weekly-summary"         # weekly retrospective
telos "monthly-summary"        # monthly retrospective
```

### Natural language routing

```bash
telos "let's start the day"                    # → kickoff
telos "let's wrap up for the day"              # → shutdown
telos "write an interstitial about the sync fix"  # → interstitial
telos "plan the week"                          # → weekly-plan
```

### Verbose mode

```bash
telos --verbose --dry-run "let's wrap up"
```

Prints routing details (agent name, skills dir, matched skill) before the result.

## Skills reference

| Skill | Description | Duration |
|-------|-------------|----------|
| `kickoff` | Morning orientation — surface yesterday's carry-over, flag tier-1 gaps, ask focus | ~2 min |
| `shutdown` | End-of-day capture — accomplishments, blockers, load metrics, tomorrow | ~3 min |
| `interstitial` | Quick timestamped note — capture a thought, observation, or decision | ~30 sec |
| `weekly-plan` | Start-of-week planning — load calculation, project triage, daily schedules | ~15 min |
| `weekly-review` | Weekly review against Clockify timesheet — time breakdown, patterns | ~10 min |
| `weekly-summary` | Weekly retrospective — project movement, GitHub metrics, patterns | ~5 min |
| `monthly-summary` | Monthly retrospective — project progress, tier-1 accountability, themes | ~5 min |

## Running the tests

From the repo root:

```bash
# all tests (unit + integration + e2e)
uv run pytest --tb=short -q

# real E2E tests (requires API key, claude binary, and Obsidian vault)
uv run pytest tests/e2e/test_cli.py::TestRealE2E -v

# dry-run routing test only
uv run pytest tests/e2e/test_cli.py::TestRealE2E::test_dry_run_with_real_api_routing -v
```

Real E2E tests install the kairos pack into an isolated environment, then run against the actual Obsidian vault with real API calls and real Claude Code.

## Uninstall

```bash
telos uninstall kairos
```

This removes the agent's skills directory, the registry entry, and the `agents.toml` stanza.
