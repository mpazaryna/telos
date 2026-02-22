# Hacker News Agent Pack

A telos agent pack that fetches and summarizes the Hacker News front page — stories grouped by theme with points, comments, and links. Uses the public HN RSS feed with no authentication required.

## What's in the pack

```
packs/hackernews/
  agent.toml       # agent metadata (name, description, working_dir)
  skills/
    frontpage/
      SKILL.md     # fetch and summarize the HN front page
```

### How it works

The frontpage skill uses `fetch_url` to pull the HN RSS feed from `hnrss.org`, parses titles, links, points, and comment counts, then groups the top ~15 stories by theme and writes formatted markdown output.

No scripts, no MCP servers, no authentication — pure `fetch_url` + `write_file`.

## Prerequisites

1. **telos** installed (`uv pip install -e .` from the repo root)
2. **ANTHROPIC_API_KEY** in `~/.config/telos/.env` (or use Ollama with `TELOS_PROVIDER=ollama`)

## Install

```bash
telos install packs/hackernews
```

Verify:

```bash
telos agents          # should show "hackernews" in the table
telos list-skills     # should show "frontpage"
```

## Usage

### Live run

```bash
telos --agent hackernews "frontpage"
```

Fetches the current HN front page and prints a themed summary.

### Dry run

```bash
telos --dry-run --agent hackernews "frontpage"
```

Routes the request and prints the matched skill without executing.

### Output

Stories are grouped under theme headers: AI / ML, Systems / Infra, Programming, Show HN, Science, Startups / Business, Culture / Other.

Each story shows:
- Bold title with a one-sentence summary
- Points and comment count in italics
- Direct link

The output is also saved to `~/obsidian/telos/hackernews/YYYY-MM-DD-frontpage.md`.

## Skills reference

| Skill | Description | Data source |
|-------|-------------|-------------|
| `frontpage` | Top ~15 HN stories grouped by theme | `hnrss.org/frontpage?count=30` |

## Uninstall

```bash
telos uninstall hackernews
```
