# telos — Build Specification

**Version:** 4.0
**Date:** 2026-02-22
**CLI Name:** `telos`
**Status:** Implemented

---

## Purpose

A lightweight Python CLI that acts as a personal agent runtime. It accepts natural
language input, routes intent to the correct skill for the correct agent, and executes
that skill via direct LLM API calls with streaming.

---

## Core Concepts

### Skill
A skill is a folder containing a `SKILL.md` file, optionally accompanied by scripts
or other supporting files. The `SKILL.md` has YAML frontmatter with a `description:`
field and a prompt body. The description is used for intent routing. The body is sent
to the LLM provider for execution.

```
apple-calendar/
  SKILL.md
  scripts/
    cal-list.sh
    cal-create.sh
    cal-read.sh
```

Compatible with [OpenClaw](https://github.com/openclaw/skills) and
[ClawHub](https://clawhub.ai). Skills from either source work without modification.

### Agent
A named profile representing a domain of work. Each agent has:
- A **pack directory** in `~/.skills/<name>/` containing an optional `agent.toml`,
  optional `mcp.json`, and a `skills/` subdirectory
- A **skills directory** (`~/.skills/<name>/skills/`) with one or more skill folders
- A **working directory** where file output is rooted (defaults to `~/obsidian/telos/<name>/`)
- A **pack directory** where `run_command` executes (so companion scripts are found)
- An optional **MCP config** (`mcp.json`) for external tool servers

Agents are discovered automatically by scanning `~/.skills/`. No registration required.

### Intent Routing
Two-pass process:
1. **Keyword match** — if the input contains an exact skill name, match directly with
   no API call. Matches longest name first to avoid collisions.
2. **LLM API match** — if no keyword match, send the skill manifest + user input to
   the routing model with `max_tokens: 64` to get the skill name.

### Cross-Agent Routing
When no `--agent` flag is provided, telos searches all agents (sorted by name) and
returns the first match. No default agent concept.

### Execution
Skills are executed via direct LLM API calls using a Provider abstraction. The provider
streams tokens to stdout and executes tool calls in a loop (up to 20 rounds). Built-in
tools are always available. MCP tools are added when the agent has an `mcp.json`.

### Dual Working Directories
- **File tools** (write_file, read_file, list_directory) resolve relative to `working_dir`
  (typically an Obsidian vault path for persistent output)
- **run_command** executes in `pack_dir` (`~/.skills/<name>/`) so companion scripts
  are found automatically

### Output Convention
Agents write to `~/obsidian/telos/<agent-name>/` by default. All output lands in the
Obsidian vault for search, backlinks, and mobile access.

---

## Provider Architecture

### Provider Protocol
```python
class Provider(Protocol):
    def stream_completion(
        self,
        system: str,
        messages: list[dict],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 16384,
    ) -> Generator[StreamEvent, None, None]: ...
```

All providers yield `StreamEvent` objects: `text` (streamed tokens), `tool_call`
(tool invocation), or `done` (completion with stop reason).

### AnthropicProvider
Default provider. Uses the `anthropic` SDK with `client.messages.stream()`. Default
model: `claude-haiku-4-5` (configurable via `TELOS_MODEL`).

### OllamaProvider
Local/offline provider. Uses the `openai` SDK against Ollama's OpenAI-compatible
endpoint. Includes message format translation from Anthropic's `tool_use`/`tool_result`
blocks to OpenAI's `tool_calls`/`role: "tool"` format.

### Provider Selection

| Variable | Default | Purpose |
|----------|---------|---------|
| `TELOS_PROVIDER` | `anthropic` | Provider backend: `anthropic` or `ollama` |
| `TELOS_MODEL` | `claude-haiku-4-5` (anthropic), `llama3.1` (ollama) | Model name |
| `ANTHROPIC_API_KEY` | — | Required for Anthropic provider |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama endpoint |

---

## Built-in Tools

Every skill execution has access to these tools, regardless of provider:

| Tool | Description |
|------|-------------|
| `write_file` | Write content to a file. Creates parent directories. |
| `read_file` | Read the contents of a file. |
| `list_directory` | List files and subdirectories. |
| `fetch_url` | Fetch content from a URL. Returns the response body. |
| `run_command` | Run a shell command and return output. 60s timeout. |

File paths resolve relative to `working_dir`. Shell commands run in `pack_dir`.

---

## MCP Integration

Agents can declare external tool servers via `mcp.json` in their pack directory.
When present, MCP tools are available alongside built-in tools during execution.

### mcp.json Format
```json
{
  "mcpServers": {
    "clickup": {
      "url": "https://mcp.clickup.com/mcp",
      "type": "http",
      "headers": {
        "Authorization": "Bearer ${CLICKUP_API_TOKEN}"
      }
    }
  }
}
```

### Supported Transports
- `sse` — Server-Sent Events (legacy)
- `http` / `streamable-http` — Streamable HTTP (preferred)

Header values support `${VAR}` interpolation from the loaded environment.

### Tool Dispatch
During execution, each tool call is routed:
- Built-in tool names → `_execute_builtin_tool()` (sync, local)
- All other names → MCP session `call_tool()` (async, remote)

---

## Logging

Every skill execution is logged to per-day JSONL files at
`~/.local/share/telos/logs/YYYY-MM-DD.jsonl`.

### Event Types

**skill_start** — emitted when execution begins:
```json
{"ts": "...", "event": "skill_start", "provider": "anthropic", "model": "claude-haiku-4-5", "has_mcp": false}
```

**tool_call** — emitted for each tool invocation:
```json
{"ts": "...", "event": "tool_call", "tool": "fetch_url", "is_error": false}
```

**skill_end** — emitted when execution completes:
```json
{"ts": "...", "event": "skill_end", "duration_s": 4.23, "rounds": 3, "tool_calls": 2, "error": null, "messages": [...]}
```

---

## Agent Discovery and Configuration

### ~/.skills/ as Canonical Source

All agents live in `~/.skills/`. Discovery scans each subdirectory for a `skills/`
folder containing at least one `*/SKILL.md`. Override the location with `TELOS_SKILLS_DIR`.

### agent.toml (Optional)

Provides metadata overrides when defaults aren't sufficient:

```toml
name = "hackernews"
description = "Hacker News reader — frontpage summaries and trending topics"
working_dir = "~/obsidian/telos/hackernews"
```

When absent, defaults are inferred:
- **name** — from the directory name
- **description** — from the first SKILL.md's frontmatter
- **working_dir** — defaults to `~/obsidian/telos/<name>/`

A bare skill folder with just a `SKILL.md` is a valid installable unit.

### agents.toml (Overrides Only)

Location: `~/.config/telos/agents.toml`

Used only for working directory overrides. No mode, no description, no default agent.

```toml
[agents.kairos]
working_dir = "~/obsidian/telos/kairos"

[agents.clickup]
working_dir = "~/obsidian/telos/clickup"

[agents.hackernews]
working_dir = "~/obsidian/telos/hackernews"
```

### Install Locations

| Path | Purpose |
|------|---------|
| `~/.skills/<name>/` | Agent pack (skills, scripts, mcp.json, agent.toml) |
| `~/.config/telos/` | Configuration (agents.toml, .env) |
| `~/.local/share/telos/logs/` | Per-day JSONL execution logs |
| `~/obsidian/telos/<name>/` | Agent output files (convention) |

### Install / Uninstall

```bash
telos install <path>      # copytree to ~/.skills/<name>/
telos uninstall <name>    # rmtree from ~/.skills/<name>/
```

Install reads optional `agent.toml` for the name (falls back to directory name),
copies the entire pack via `shutil.copytree`, and prints a summary. No registry,
no config merge — discovery handles everything.

---

## Current Agents

| Agent | Description | Output Dir |
|-------|-------------|------------|
| kairos | Personal productivity — daily notes, summaries | Obsidian vault |
| hackernews | HN frontpage summaries | `~/obsidian/telos/hackernews/` |
| clickup | Project standup via MCP | `~/obsidian/telos/clickup/` |
| apple-calendar | Calendar.app integration (ported from OpenClaw) | stdout |
| arxiv | arXiv paper summaries | `~/obsidian/telos/arxiv/` |

---

## Technology Stack

| Concern | Choice |
|---------|--------|
| Language | Python 3.12+ |
| Package management | `uv` |
| CLI framework | `typer` |
| Terminal output | `rich` |
| TOML parsing | `tomllib` (stdlib) |
| TOML writing | `tomli_w` |
| API routing calls | `anthropic` SDK |
| Skill execution | Direct API via Provider protocol |
| Anthropic provider | `anthropic` SDK |
| Ollama provider | `openai` SDK (OpenAI-compatible) |
| MCP client | `mcp` SDK |
| Logging | JSONL (stdlib `json`) |

---

## Project Structure

```
telos/
├── pyproject.toml
├── uv.lock
├── CLAUDE.md
├── docs/
│   └── skill-example/          # annotated example of a SKILL.md
│       ├── README.md
│       └── frontpage/SKILL.md
├── .orchestra/
│   ├── specs/
│   │   └── bootstrap.md        # this file
│   └── adr/
├── tests/
│   ├── unit/
│   │   ├── test_config.py
│   │   ├── test_router.py
│   │   ├── test_executor.py
│   │   ├── test_installer.py
│   │   ├── test_provider.py
│   │   ├── test_mcp_client.py
│   │   └── test_logger.py
│   ├── integration/
│   │   ├── test_pipeline.py
│   │   └── test_config_router.py
│   └── e2e/
│       └── test_cli.py
└── src/
    └── telos/
        ├── __init__.py
        ├── __main__.py
        ├── main.py               # Typer app, all CLI commands
        ├── config.py             # agent discovery from ~/.skills/ + overrides
        ├── router.py             # skill discovery, intent routing
        ├── executor.py           # execution engine, tool loops, dual cwd
        ├── provider.py           # Provider protocol, Anthropic + Ollama
        ├── mcp_client.py         # MCP SSE/HTTP client
        ├── logger.py             # per-day JSONL logging
        ├── installer.py          # pack install/uninstall (copytree to ~/.skills/)
        ├── interactive.py        # interactive agent/skill selection
        └── discord_bot.py        # Discord bot frontend
```

---

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | Yes (for Anthropic) | API key for routing and execution |
| `TELOS_PROVIDER` | No | Provider backend: `anthropic` (default) or `ollama` |
| `TELOS_MODEL` | No | Override model name |
| `TELOS_SKILLS_DIR` | No | Override skills directory (default: `~/.skills/`) |
| `TELOS_CONFIG_DIR` | No | Override config directory |
| `TELOS_DATA_DIR` | No | Override data directory |
| `OLLAMA_BASE_URL` | No | Ollama endpoint (default: `http://localhost:11434/v1`) |
| `CLICKUP_API_TOKEN` | No | Required by clickup MCP server |
| `DISCORD_BOT_TOKEN` | No | Required for Discord bot |

Optional `.env` file at `~/.config/telos/.env` is loaded before provider creation
and MCP header interpolation.

---

## CLI Commands

### Core
```
telos                               # launch interactive mode
telos "<request>"                   # route across all agents
telos --agent <name> "<request>"   # route within a specific agent
telos --dry-run "<request>"        # show matched skill, do not execute
telos --verbose "<request>"        # show routing details, then execute
```

### Discovery
```
telos list-skills                    # list all skills across agents
telos list-skills --agent <name>   # list skills for one agent
telos agents                        # list all discovered agents
```

### Agent Management
```
telos install <path>                # install agent pack to ~/.skills/
telos uninstall <name>             # remove agent from ~/.skills/
```

### Setup
```
telos init                          # create config dir and ~/.skills/
```

### Discord
```
telos bot                           # start the Discord bot
```

---

## Execution Flow

```
User Input
    │
    ▼
main.py: _handle_request()
    ├── load_config() — discover from ~/.skills/, merge agents.toml overrides
    ├── _route_across_agents() — search all agents (or --agent specific)
    │   ├── discover_skills() for each agent
    │   └── route_intent()
    │       ├── keyword_match() — longest substring first
    │       └── api_route() — LLM API if no keyword match
    └── execute_skill()
        │
        ▼
executor.py: execute_skill()
    ├── load_env() from ~/.config/telos/.env
    ├── _create_provider() → Anthropic or Ollama
    ├── _build_prompt() — skill body + user request + timestamp
    ├── log_skill_start()
    └── _execute_simple() or _execute_with_mcp()
        │
        ▼
    Tool-use loop (max 20 rounds):
        ├── provider.stream_completion() → text + tool_calls
        ├── stream text to stdout
        ├── for each tool_call:
        │   ├── built-in tool → _execute_builtin_tool(cwd=working_dir, command_cwd=pack_dir)
        │   └── MCP tool → mcp_ctx.call_tool()
        │   └── log_tool_call()
        ├── append results to messages
        └── repeat until no tool_calls
        │
        ▼
    log_skill_end() with duration, rounds, messages
```

---

## Skill File Format

```
skills/
├── kickoff/
│   └── SKILL.md
├── standup/
│   └── SKILL.md
```

Every `SKILL.md` must have YAML frontmatter with a `description` field:

```markdown
---
description: Quick morning orientation. Surface what matters, set focus.
---

# Kickoff

[full skill prompt body here]

## Save output
After printing, also write to a file named `YYYY-MM-DD-kickoff.md`.
```

Skills without `description` frontmatter are registered with description
`"(no description)"`.

See `docs/skill-example/` for an annotated example.

---

## Implementation Notes

1. **No packs/ in repo** — skills live in `~/.skills/`. The repo ships a single
   annotated example in `docs/skill-example/`.

2. **No subprocess** — execution is direct API calls, not `claude` CLI subprocess.

3. **Provider protocol** — `stream_completion()` is a sync Generator. The async
   boundary exists only in MCP client connections.

4. **Message format** — internal messages use Anthropic format (`tool_use`/
   `tool_result` content blocks). OllamaProvider translates to OpenAI format
   internally via `_convert_messages()`.

5. **Keyword matching** — longest skill name first to avoid partial collisions.

6. **Frontmatter parsing** — simple string split on `---` delimiters. No YAML library.

7. **Rich** for all CLI output. No raw `print()`.

8. **pathlib.Path** for all path handling. Never string concatenation.

9. **uv** is the only package manager.

10. **tomli_w** for TOML writing. Never string-concatenate TOML.

---

## Future Considerations

- **Remote install sources** — `telos install clawhub:<slug>`,
  `telos install github:<user>/<repo>`. Fetch the skill folder, install normally.
- **Additional providers** — Apple Foundation Models, OpenAI. Just implement
  `stream_completion()`.
- **Cost tracking** — Parse token counts from provider responses, log to JSONL.
