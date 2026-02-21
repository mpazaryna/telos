# telos

A [clawbot](https://github.com/openclaw/skills) with its own engine. Compatible with the OpenClaw skill ecosystem, powered by direct API calls instead of Claude Code.

```
telos "hacker news frontpage"
telos --agent clickup "standup"
telos --agent apple-calendar "list my calendars"
```

## What's a clawbot?

A **claw** is a `SKILL.md` file — a markdown document that tells an LLM what to do, what tools to use, and how to format the output. The [OpenClaw](https://github.com/openclaw/skills) ecosystem is a growing library of community-contributed skills for everything from Apple Calendar to GitHub to Hacker News.

A **clawbot** is a runtime that executes claws. Most clawbots wrap `claude -p` (Claude Code as a subprocess). Telos takes a different approach: it calls the Anthropic API directly with its own tool-use loop and provider abstraction. Same skills, different engine.

This means:
- **No Claude Code dependency.** No 5-10s Node.js cold start per execution.
- **Provider-agnostic.** Anthropic by default, Ollama for local/offline. Swap with one env var.
- **OpenClaw compatible.** Pull skills from the ecosystem and they just work — we ported [apple-calendar](https://github.com/openclaw/skills/tree/main/skills/tyler6204/apple-calendar) in minutes.
- **Small enough to audit.** The entire engine is under 1000 lines of Python.

## Why this matters

For decades, the runtime *was* the moat. You paid Oracle for the database, Salesforce for the CRM, Microsoft for the BI layer. The logic, the workflows, the integrations — all locked inside proprietary runtimes. You couldn't take your stuff and leave. That was the business model.

Now a skill is a markdown file. The logic is human-readable. The integrations are MCP servers anyone can stand up. The model is an API call. There's nothing left to lock in.

The runtime is commoditized. Claude Code, Telos, Claws, Codex, Gemini — they're all just different ways to read a prompt, call an API, and execute tools. The value isn't in the runtime anymore. The value is in the **skills** (the accumulated knowledge of *how* to do something) and the **models** (the intelligence that interprets them). Everything in between is interchangeable plumbing.

The entire enterprise software industry was built on the premise that the runtime is where value accumulates. That premise just broke.

## How it works

```
"summarize hacker news" → route → hackernews:frontpage → Anthropic API → stream to stdout
                                                        → fetch_url(hnrss.org)
                                                        → write_file(2026-02-21-frontpage.md)
```

1. **Route** — keyword match first (zero API cost), then Claude API for fuzzy intent
2. **Execute** — stream completion with tools in a loop (up to 20 rounds)
3. **Tools** — built-in file I/O + URL fetching, plus MCP servers for external APIs
4. **Persist** — output streams to terminal and saves to `~/telos/<agent>/`

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

Initialize and install the bundled packs:

```bash
uv run telos init
uv run telos install packs/hackernews
uv run telos install packs/clickup
uv run telos install packs/kairos
```

## Usage

```bash
# Run against default agent
uv run telos "run daily kickoff"

# Target a specific agent
uv run telos --agent hackernews "frontpage"

# See what would match without executing
uv run telos --dry-run "standup"

# Interactive mode — browse agents and skills
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

The `SKILL.md` is the entire configuration:

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

This is the same format used by [OpenClaw](https://github.com/openclaw/skills) and [ClawHub](https://clawhub.ai). A skill pulled from any source works in telos without modification. The `agent.toml` wrapper that telos uses for installation is scaffolding — the skill itself is just the folder. Making `agent.toml` optional is on the roadmap, which will enable direct install from ClawHub, GitHub, or any URL.

## Agents

An agent is a named profile with a skills directory and a working directory:

| Agent | Description | Output |
|-------|-------------|--------|
| kairos | Personal productivity — daily notes, weekly summaries (Obsidian) | Obsidian vault |
| hackernews | HN frontpage summaries | `~/telos/hackernews/` |
| clickup | Project standup via MCP | `~/telos/clickup/` |
| apple-calendar | Calendar.app integration (ported from OpenClaw) | stdout |

Agents come in two modes:
- **Linked** — skills live in an external directory (e.g. Obsidian vault), read live on every run
- **Installed** — skills managed by telos at `~/.local/share/telos/agents/`

## Providers

Telos uses a Provider protocol. Swap backends with environment variables:

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

Every skill has access to:

| Tool | Purpose |
|------|---------|
| `write_file` | Write content to a file (creates dirs) |
| `read_file` | Read file contents |
| `list_directory` | List directory entries |
| `fetch_url` | Fetch a URL and return the body |
| `run_command` | Run a shell command (60s timeout) |

File paths resolve relative to the agent's `working_dir`. Shell commands run in the same directory.

## MCP integration

Agents can connect to external tool servers via `mcp.json`:

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

MCP tools and built-in tools are available side by side during execution.

## Logging

Every execution is logged to `~/.local/share/telos/logs/YYYY-MM-DD.jsonl`:

```json
{"ts": "...", "event": "skill_start", "provider": "anthropic", "model": "claude-haiku-4-5", "has_mcp": false}
{"ts": "...", "event": "tool_call", "tool": "fetch_url", "is_error": false}
{"ts": "...", "event": "skill_end", "duration_s": 4.2, "rounds": 3, "tool_calls": 2, "error": null, "messages": [...]}
```

## Project structure

```
src/telos/
  main.py           # CLI commands (typer)
  config.py         # agents.toml loading
  router.py         # skill discovery + intent routing
  executor.py       # execution engine, tool loops
  provider.py       # Provider protocol, Anthropic + Ollama
  mcp_client.py     # MCP SSE/HTTP client
  logger.py         # per-day JSONL logging
  installer.py      # pack install/uninstall
  interactive.py    # interactive mode
```

## License

MIT
