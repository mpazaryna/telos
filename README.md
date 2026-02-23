# telos

*Telos* (τέλος) — Greek for "end" or "purpose." The telos of a thing is the reason it exists. An acorn's telos is an oak tree. A knife's telos is to cut.

The telos of a runtime is to disappear. This one is getting close.

A lightweight agent runtime. Skills are markdown files, models are API calls, the whole thing runs locally in under 1000 lines of Python.

```
telos "hacker news frontpage"
telos --agent clickup "standup"
telos --agent apple-calendar "list my calendars"
```

## What it does

You type natural language. Telos routes to the right skill and executes it via direct LLM API calls with tool use. A skill is a `SKILL.md` file — markdown that tells the model what to do, what tools to use, how to format the output. No DSL, no pipeline config, no framework lock-in.

- **Provider-agnostic.** Anthropic by default, Ollama for local/offline. One env var to swap.
- **OpenClaw compatible.** Skills from the [ecosystem](https://github.com/openclaw/skills) just work.
- **Discord included.** Built-in bot, same routing, run skills from any device.
- **Small enough to audit.** The whole engine fits in your head.

## Why it's built this way

The runtime used to be the moat. You paid Oracle for the database, Salesforce for the CRM, Microsoft for the BI layer. Your logic was locked inside their runtime. That was the business model.

Now a skill is a markdown file. The integrations are MCP servers anyone can stand up. The model is an API call. There's nothing left to lock in.

The value is in the skills — the accumulated knowledge of *how* to do something — and the models that interpret them. Everything in between is plumbing. Write a skill once, run it anywhere.

## Skills as personal assets

In the early 1990s a spreadsheet was a personal asset. You built it yourself, encoding domain knowledge into formulas nobody else had. The tool that ran it (Lotus 1-2-3, then Excel) was interchangeable. What mattered was the `.xls`.

Skills are the same pattern, one level up. A `SKILL.md` encodes domain expertise — how to summarize a frontpage, run a standup, triage a calendar — in a file any runtime can execute. You keep it in `~/.skills/`. You carry it between machines. The runtime is plumbing. The skill is the asset.

The difference is what sits between the file and the output. A spreadsheet had a formula engine. A skill has an LLM. The formulas were rigid — `=SUM(B2:B10)`. The instructions are natural language — *"fetch the RSS feed, group by theme, write a summary."* Same pattern: portable files, interchangeable engines. But the ceiling on what a single file can do is incomparably higher.

`~/.skills/` is a personal library — like `~/Documents` but for automation. Each skill compounds over time. Twenty skills for your domain is twenty reusable assets that work with any model, on any runtime, from any device.

## How it compares

The pattern is converging. [Goose](https://github.com/block/goose) (Block), Claude Code, Codex — everyone is landing on the same architecture: markdown skills, model API calls, tool use, MCP. The differences are packaging.

| | Telos | Goose | Claude Code |
|---|---|---|---|
| Language | Python (~1000 LOC) | Rust | Node.js |
| Skills format | SKILL.md | SKILL.md (OpenClaw) | commands/ |
| Providers | Anthropic, Ollama | Multi-provider | Anthropic only |
| MCP support | Yes | Yes | Yes |
| Discord bot | Built-in | Community experiment | No |
| Persistence | Obsidian vault | Filesystem | Filesystem |
| Codebase | Fits in your head | Large | Proprietary |

Telos is small by design. The value isn't in the runtime.

## How it works

```
"summarize hacker news" → route → hackernews:frontpage → Anthropic API → stream to stdout
                                                        → fetch_url(hnrss.org)
                                                        → write_file(2026-02-21-frontpage.md)
```

1. **Route** — keyword match first (zero API cost), then LLM for fuzzy intent
2. **Execute** — stream completion with tools in a loop (up to 20 rounds)
3. **Tools** — built-in file I/O + URL fetching, plus MCP servers for external APIs
4. **Persist** — output streams to terminal and saves to `~/obsidian/telos/<agent>/`

## Install

```bash
git clone https://github.com/mpazaryna/telos.git
cd telos
uv sync
```

Set up your environment:

```bash
mkdir -p ~/.config/telos
cat > ~/.config/telos/.env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-...
EOF
```

Install the bundled packs:

```bash
uv run telos init
uv run telos install packs/hackernews
uv run telos install packs/clickup
uv run telos install packs/kairos
```

Packs land in `~/.skills/` and are discovered automatically. Override with `TELOS_SKILLS_DIR`.

## Usage

```bash
# Routes across all agents
uv run telos "run daily kickoff"

# Target a specific agent
uv run telos --agent hackernews "frontpage"

# Dry run — see what matches without executing
uv run telos --dry-run "standup"

# Interactive mode
uv run telos
```

## Skills

A skill is a folder with a `SKILL.md` and optionally companion scripts:

```
apple-calendar/
  SKILL.md
  scripts/
    cal-list.sh
    cal-create.sh
    cal-read.sh
```

The `SKILL.md` is the whole configuration:

```markdown
---
description: Summarize the current Hacker News front page
---

# Hacker News Frontpage

1. Fetch the RSS feed from `https://hnrss.org/frontpage?count=30`
2. Parse titles, links, points, and comment counts
3. Summarize the top stories grouped by theme

## Save output
Write to `YYYY-MM-DD-frontpage.md`.
```

No config files. No pipeline DSL. The skill *is* the configuration.

Compatible with [OpenClaw](https://github.com/openclaw/skills) and [ClawHub](https://clawhub.ai) — skills from either source work without modification. The `agent.toml` wrapper is scaffolding. The skill itself is just the folder.

## Agents

An agent is a named profile with a skills directory and a working directory:

| Agent | What it does | Output |
|-------|-------------|--------|
| kairos | Daily notes, weekly summaries (Obsidian) | Obsidian vault |
| hackernews | HN frontpage summaries | `~/obsidian/telos/hackernews/` |
| clickup | Project standup via MCP | `~/obsidian/telos/clickup/` |
| apple-calendar | Calendar.app integration (ported from OpenClaw) | stdout |

Agents live in `~/.skills/` and are discovered automatically. Each agent is a directory with a `skills/` subdirectory. Optional `agent.toml` for metadata overrides. `agents.toml` for working directory overrides only.

## Providers

Swap backends with environment variables:

```bash
# Anthropic (default)
TELOS_PROVIDER=anthropic
TELOS_MODEL=claude-haiku-4-5

# Ollama (local)
TELOS_PROVIDER=ollama
TELOS_MODEL=llama3.1
OLLAMA_BASE_URL=http://localhost:11434/v1
```

## Built-in tools

Every skill gets these:

| Tool | What it does |
|------|---------|
| `write_file` | Write content to a file (creates dirs) |
| `read_file` | Read file contents |
| `list_directory` | List directory entries |
| `fetch_url` | Fetch a URL and return the body |
| `run_command` | Run a shell command (60s timeout) |

File paths resolve relative to `working_dir` (output directory). Shell commands run in `pack_dir` (`~/.skills/<name>/`) so companion scripts are found automatically.

## MCP

Agents connect to external tool servers via `mcp.json`:

```json
{
  "mcpServers": {
    "clickup": {
      "url": "https://mcp.clickup.com/mcp",
      "type": "http",
      "headers": { "Authorization": "Bearer ${CLICKUP_API_TOKEN}" }
    }
  }
}
```

MCP tools and built-in tools are available side by side.

## Discord bot

Built-in bot. Runs locally, connects to your server. Same routing, same skills — type in a `#telos` channel instead of a terminal.

```bash
echo 'DISCORD_BOT_TOKEN=your-token-here' >> ~/.config/telos/.env
uv run telos bot
```

Or run as a launchd service (auto-starts on login, restarts on crash):

```bash
launchctl load ~/Library/LaunchAgents/com.telos.discord-bot.plist
```

In Discord:

```
frontpage                              # routes across all agents
--agent arxiv trending in cs.CL       # target a specific agent
--agent clickup standup                # MCP skills work too
```

Management:

```bash
launchctl list | grep telos                                        # running?
tail -f ~/.local/share/telos/logs/discord-bot.log                  # logs
launchctl kickstart -k gui/$(id -u)/com.telos.discord-bot          # restart
launchctl unload ~/Library/LaunchAgents/com.telos.discord-bot.plist # stop
```

## Logging

Every run is logged to `~/.local/share/telos/logs/YYYY-MM-DD.jsonl`:

```json
{"ts": "...", "event": "skill_start", "provider": "anthropic", "model": "claude-haiku-4-5", "has_mcp": false}
{"ts": "...", "event": "tool_call", "tool": "fetch_url", "is_error": false}
{"ts": "...", "event": "skill_end", "duration_s": 4.2, "rounds": 3, "tool_calls": 2, "error": null, "messages": [...]}
```

## Project structure

```
src/telos/
  main.py           # CLI (typer)
  config.py         # agent discovery from ~/.skills/ + overrides
  router.py         # skill discovery + intent routing
  executor.py       # execution engine, tool loops
  provider.py       # Provider protocol, Anthropic + Ollama
  mcp_client.py     # MCP SSE/HTTP client
  logger.py         # per-day JSONL logging
  installer.py      # pack install/uninstall to ~/.skills/
  interactive.py    # interactive mode
  discord_bot.py    # Discord bot
```

## License

MIT
