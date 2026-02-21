# telos

A personal agent runtime. Route natural language to skills, execute via direct LLM calls — from anywhere on the filesystem.

Telos is a lightweight Python CLI that sits between you and your LLM. You speak naturally; it routes your intent to the right skill, calls the API, executes tools, and streams the result. No 400K-line runtimes, no cloud dependencies, no config DSLs. Skills are markdown files. The core is under 1000 lines.

```
telos "hacker news frontpage"
telos --agent clickup "standup"
telos "write an interstitial about the API refactor"
```

## Why

LLM agents are powerful but the orchestration layer is a mess — bloated runtimes, vibe-coded monsters, security nightmares. Telos takes the opposite approach:

- **Small enough to audit.** The entire engine fits in your head.
- **Skills over config.** No YAML pipelines, no if-then-else monsters. A skill is a markdown file that tells the LLM what to do. Want to change how your standup report works? Edit the markdown.
- **Provider-agnostic.** Anthropic by default, Ollama for local/offline. Swap with one env var.
- **Local-first.** Your keys stay in a local `.env`. Run against cloud APIs or a model on your desk.

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

A skill is a markdown file in a subdirectory:

```
packs/hackernews/
  agent.toml
  skills/
    frontpage/
      SKILL.md
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

## Agents

An agent is a named profile with a skills directory and a working directory:

| Agent | Description | Output |
|-------|-------------|--------|
| kairos | Personal productivity — daily notes, weekly summaries (Obsidian) | Obsidian vault |
| hackernews | HN frontpage summaries | `~/telos/hackernews/` |
| clickup | Project standup via MCP | `~/telos/clickup/` |

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

File paths resolve relative to the agent's `working_dir`.

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
