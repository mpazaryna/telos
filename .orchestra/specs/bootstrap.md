# telos CLI — Build Specification

**Version:** 3.0
**Date:** 2026-02-21
**CLI Name:** `telos`
**Status:** Implemented

---

## Purpose

A lightweight Python CLI that acts as a personal agent runtime. It accepts natural
language input, routes intent to the correct skill for the correct agent, and executes
that skill via direct LLM API calls with streaming — from anywhere on the filesystem.

The user speaks naturally; the CLI handles routing, provider selection, tool execution,
and output persistence.

---

## Core Concepts

### Telos as a Clawbot

Telos is a [clawbot](https://github.com/openclaw/skills) — a runtime that executes
claws (SKILL.md files). It is compatible with the [OpenClaw](https://github.com/openclaw/skills)
skill ecosystem and [ClawHub](https://clawhub.ai) registry.

Most clawbots are tied to a single runtime like Claude Code. Telos has its own execution
engine with a provider abstraction — same skills, any model. This means no single-vendor
lock-in, no subprocess overhead, and the ability to swap providers (Anthropic, Ollama,
etc.) with an env var.

The `SKILL.md` file is the universal contract. A skill written for any clawbot works in
telos. The runtime is interchangeable — the skill is the product.

### Skill (Claw)
A skill is a folder containing a `SKILL.md` file, optionally accompanied by scripts,
README, or other supporting files. The `SKILL.md` has YAML frontmatter with a
`description:` field and a prompt body. The description is used for intent routing.
The body is sent to the LLM provider for execution.

```
apple-calendar/
  SKILL.md
  scripts/
    cal-list.sh
    cal-create.sh
    cal-read.sh
```

This is the same format used by OpenClaw and ClawHub. A skill pulled from any source
can be installed in telos without modification.

### Agent
A named profile representing a domain of work. Each agent has:
- A **skills directory** containing one or more skill folders (each with a `SKILL.md`)
- A **working directory** where file operations are rooted (defaults to `~/obsidian/telos/<name>/`)
- A **mode**: `linked` (reads live from an external directory, e.g. Obsidian vault) or
  `installed` (skills managed by telos in `~/.local/share/telos/agents/`)
- An optional **MCP config** (`mcp.json`) for external tool servers

### Intent Routing
Two-pass process:
1. **Keyword match** — if the input contains an exact skill name (e.g. `kickoff`),
   match directly with no API call. Matches longest name first to avoid collisions.
2. **Claude API match** — if no keyword match, send the skill manifest + user input to
   `claude-sonnet-4-6` with `max_tokens: 64` to get the skill name. Requires
   `ANTHROPIC_API_KEY` in environment.

### Execution
Skills are executed via direct LLM API calls using a **Provider** abstraction. The
provider streams tokens to stdout and executes tool calls in a loop (up to 20 rounds).
Built-in tools (file I/O, URL fetching) are always available. MCP tools are added when
the agent has an `mcp.json` config.

### Output Convention
Agents that produce artifacts write to `~/obsidian/telos/<agent-name>/` with dated filenames
(e.g. `2026-02-21-frontpage.md`). This is configured via `working_dir` in `agent.toml`.
Linked agents (e.g. kairos → Obsidian) write to their own directory instead.

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
endpoint at `http://localhost:11434/v1`. Includes message format translation from
Anthropic's `tool_use`/`tool_result` blocks to OpenAI's `tool_calls`/`role: "tool"`
format.

### Provider Selection
Controlled by environment variables:

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
| `write_file` | Write content to a file. Creates parent directories if needed. |
| `read_file` | Read the contents of a file. |
| `list_directory` | List files and subdirectories. |
| `fetch_url` | Fetch content from a URL. Returns the response body as text. |
| `run_command` | Run a shell command and return output. 60 second timeout. |

All file paths are resolved relative to the agent's `working_dir`. Shell commands
run in the same directory.

---

## MCP Integration

Agents can declare external tool servers via `mcp.json`. When present, MCP tools are
available alongside built-in tools during execution.

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

The `messages` array in `skill_end` contains the full conversation history for
debugging and analysis.

---

## Agent Modes

### Linked Mode
For agents backed by an external directory the user actively edits (e.g. an Obsidian
vault). Skills are read live on every invocation — no sync, no cache, no install step.

### Installed Mode
For agents whose skills are managed by telos. Skills are installed to
`~/.local/share/telos/agents/{agent-name}/skills/` via `telos install`. MCP configs
are auto-detected from the agent's data directory.

---

## Install Model

### Agent Pack Format

A pack is a directory containing one or more skills with an optional `agent.toml`:

```
my-agent-pack/
├── agent.toml          # optional — overrides for name, working_dir, etc.
├── mcp.json            # optional — MCP server config
├── scripts/            # optional — companion shell scripts
└── skills/
    ├── check-email/
    │   └── SKILL.md
    └── triage/
        └── SKILL.md
```

### agent.toml (Optional)

The `agent.toml` provides explicit configuration when defaults aren't sufficient:

```toml
name = "hackernews"
description = "Hacker News reader — frontpage summaries and trending topics"
working_dir = "~/obsidian/telos/hackernews"
```

**When `agent.toml` is present**, its values are used directly.

**When `agent.toml` is absent** (future), sensible defaults are inferred:
- **name** — derived from the directory name
- **description** — extracted from the first SKILL.md's frontmatter
- **working_dir** — defaults to `~/obsidian/telos/<name>/`

This means a bare skill folder with just a `SKILL.md` (and optionally scripts) is a
valid installable unit. The `agent.toml` is scaffolding for the exception cases:
overriding the working directory (e.g. kairos → Obsidian vault), grouping multiple
skills, or adding metadata.

Currently `agent.toml` is still required by the installer. Making it optional is a
planned enhancement that would enable direct install from ClawHub, OpenClaw, or any
source that provides a bare SKILL.md folder.

When installed, telos sets `mode = "installed"` automatically.

When `working_dir` is `"."`, telos uses the current working directory at invocation
time. When it's a path like `~/obsidian/telos/hackernews`, that path is used and created on
first write.

### Install Locations

| Path | Purpose |
|------|---------|
| `~/.config/telos/` | Configuration (agents.toml, .env) |
| `~/.local/share/telos/agents/{name}/skills/` | Installed skill files |
| `~/.local/share/telos/agents/{name}/mcp.json` | Installed MCP config |
| `~/.local/share/telos/registry.toml` | Tracks installed agents |
| `~/.local/share/telos/logs/` | Per-day JSONL execution logs |
| `~/obsidian/telos/{agent-name}/` | Agent output files (convention) |

### Install Sources (v1)
```bash
telos install ./path/to/agent-pack     # local directory
```

### Install Behavior
When `telos install ./my-agent-pack` is run:
1. Read `agent.toml` from the source directory
2. Copy `skills/*/SKILL.md` to `~/.local/share/telos/agents/{name}/skills/`
3. Copy `mcp.json` if present
4. Register in `~/.local/share/telos/registry.toml`
5. Merge agent config into `~/.config/telos/agents.toml`
6. Print summary: agent name, skill count, install path

### Uninstall
```bash
telos uninstall hackernews
```
Removes skills directory, registry entry, and config stanza. Prompts for confirmation.
Blocks on linked agents (must edit agents.toml manually).

---

## Current Agents

| Agent | Mode | Description | Output Dir |
|-------|------|-------------|------------|
| kairos | linked | Personal productivity — daily notes, summaries, load tracking. Skills live in Obsidian vault. | Obsidian vault |
| hackernews | installed | Hacker News frontpage summaries. | `~/obsidian/telos/hackernews/` |
| clickup | installed | ClickUp task review and project standup (via MCP). | `~/obsidian/telos/clickup/` |
| apple-calendar | installed | Calendar.app integration (ported from OpenClaw). | stdout |

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
| Config location | `~/.config/telos/` |
| Data location | `~/.local/share/telos/` |

---

## Project Structure

```
telos/
├── pyproject.toml
├── uv.lock
├── specs/
│   └── bootstrap.md              # this file
├── packs/                         # bundled agent packs
│   ├── kairos/
│   │   ├── agent.toml
│   │   └── skills/
│   │       ├── kickoff/SKILL.md
│   │       ├── shutdown/SKILL.md
│   │       ├── interstitial/SKILL.md
│   │       ├── weekly-plan/SKILL.md
│   │       ├── weekly-review/SKILL.md
│   │       ├── weekly-summary/SKILL.md
│   │       └── monthly-summary/SKILL.md
│   ├── hackernews/
│   │   ├── agent.toml
│   │   └── skills/
│   │       └── frontpage/SKILL.md
│   └── clickup/
│       ├── agent.toml
│       ├── mcp.json
│       └── skills/
│           └── standup/SKILL.md
├── tests/
│   ├── unit/
│   │   ├── test_config.py
│   │   ├── test_router.py
│   │   ├── test_executor.py
│   │   ├── test_installer.py
│   │   ├── test_provider.py
│   │   ├── test_mcp_client.py
│   │   └── test_logger.py
│   └── integration/
│       └── test_pipeline.py
└── src/
    └── telos/
        ├── __init__.py
        ├── __main__.py
        ├── main.py               # Typer app, all CLI commands
        ├── config.py             # agents.toml loading, Agent dataclass
        ├── router.py             # skill discovery, intent routing
        ├── executor.py           # skill execution engine, tool loops
        ├── provider.py           # Provider protocol, Anthropic + Ollama
        ├── mcp_client.py         # MCP SSE/HTTP client
        ├── logger.py             # per-day JSONL logging
        ├── installer.py          # agent pack install/uninstall
        └── interactive.py        # interactive agent/skill selection
```

---

## pyproject.toml

```toml
[project]
name = "telos"
version = "0.1.0"
description = "Personal agent runtime — route natural language to skills, execute via Claude Code"
requires-python = ">=3.12"

dependencies = [
    "typer>=0.12",
    "rich>=13.0",
    "anthropic>=0.40",
    "tomli_w>=1.0",
    "mcp>=1.0",
    "openai>=1.0",
]

[project.scripts]
telos = "telos.main:app"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-mock>=3.0",
    "pytest-asyncio>=0.23",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

## agents.toml Schema

Location: `~/.config/telos/agents.toml`
Fallback (dev only): `{project_root}/config/agents.toml`

```toml
[defaults]
default_agent = "kairos"

[agents.kairos]
mode        = "linked"
description = "Personal productivity system — daily notes, weekly/monthly summaries"
skills_dir  = "~/Documents/ObsidianVault/.claude/commands"
working_dir = "~/Documents/ObsidianVault"

[agents.hackernews]
mode        = "installed"
description = "Hacker News reader — frontpage summaries and trending topics"
# skills_dir is implicit: ~/.local/share/telos/agents/hackernews/skills/
working_dir = "~/obsidian/telos/hackernews"

[agents.clickup]
mode        = "installed"
description = "ClickUp task review and project status"
# skills_dir is implicit: ~/.local/share/telos/agents/clickup/skills/
# mcp_config is auto-detected: ~/.local/share/telos/agents/clickup/mcp.json
working_dir = "~/obsidian/telos/clickup"
```

**Field definitions:**
- `mode`: `"linked"` reads from an explicit `skills_dir` path; `"installed"` reads
  from `~/.local/share/telos/agents/{name}/skills/`.
- `skills_dir`: Required for linked agents. Ignored for installed agents (derived).
- `working_dir`: Directory where file tool operations are rooted. For installed agents,
  `~/obsidian/telos/{name}` is the convention for persistent output.
- `mcp_config`: Optional path to `mcp.json`. Auto-detected for installed agents if
  the file exists in the agent's data directory.

---

## Skill File Format

Skills live in named subdirectories as `SKILL.md`:

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

---

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | Yes (for Anthropic) | API key for routing and execution |
| `TELOS_PROVIDER` | No | Provider backend: `anthropic` (default) or `ollama` |
| `TELOS_MODEL` | No | Override model name |
| `OLLAMA_BASE_URL` | No | Ollama endpoint (default: `http://localhost:11434/v1`) |
| `CLICKUP_API_TOKEN` | No | Required by clickup MCP server |
| `TELOS_CONFIG_DIR` | No | Override config directory |
| `TELOS_DATA_DIR` | No | Override data directory |

Optional `.env` file at `~/.config/telos/.env` is loaded into the environment before
provider creation and MCP header interpolation.

---

## CLI Commands

### Core
```
telos                               # launch interactive mode
telos "<request>"                    # run request against default agent
telos --agent <name> "<request>"    # run request against named agent
telos --dry-run "<request>"         # show matched skill, do not execute
telos --verbose "<request>"         # show routing details, then execute
```

### Discovery
```
telos list-skills                    # list skills for default agent
telos list-skills --agent <name>    # list skills for named agent
telos agents                         # list all registered agents
```

### Agent Management
```
telos install <path>                 # install agent pack from local directory
telos uninstall <agent-name>         # remove installed agent and its skills
```

### Setup
```
telos init                           # create starter config at ~/.config/telos/
```

---

## Execution Flow

```
User Input
    │
    ▼
main.py: _handle_request()
    ├── load agents.toml
    ├── resolve agent (--agent flag or default)
    ├── discover_skills() from skills_dir
    ├── route_intent()
    │   ├── keyword_match() — longest substring first
    │   └── api_route() — Claude API if no keyword match
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
        │   ├── built-in tool → _execute_builtin_tool()
        │   └── MCP tool → mcp_ctx.call_tool()
        │   └── log_tool_call()
        ├── append results to messages
        └── repeat until no tool_calls
        │
        ▼
    log_skill_end() with duration, rounds, messages
```

---

## Gherkin Feature Specifications

---

### Feature: CLI Entrypoint

```gherkin
Feature: telos CLI entrypoint
  As a developer using the telos CLI
  I want to invoke any registered agent skill with natural language
  So that I can run agent commands from anywhere on the filesystem

  Scenario: Launch interactive mode with no arguments
    Given the CLI is installed and configured
    When I run `telos` with no arguments
    Then the CLI launches interactive mode
    And displays a list of agents to choose from
    And prompts for skill selection after agent is chosen

  Scenario: Invoke default agent with natural language
    Given the default agent is "kairos"
    When I run `telos "run daily kickoff"`
    Then the CLI routes the intent to the kairos agent
    And executes the "kickoff" skill via the configured provider
    And output streams to the terminal

  Scenario: Invoke a specific agent explicitly
    Given agents "kairos", "hackernews", and "clickup" are registered
    When I run `telos --agent hackernews "frontpage"`
    Then the CLI routes the intent to the hackernews agent
    And executes the matching skill

  Scenario: No matching skill found
    When I run `telos "order me a pizza"`
    Then the CLI prints "No matching skill found for: 'order me a pizza'"
    And lists available skills for the default agent
    And exits with a non-zero status code

  Scenario: Dry run shows matched skill without executing
    When I run `telos --dry-run "run daily kickoff"`
    Then the CLI prints the matched agent name and skill name
    And does not call the LLM provider
    And exits with status 0

  Scenario: Verbose mode shows routing details before executing
    When I run `telos --verbose "weekly summary"`
    Then the CLI prints the agent name, skills_dir path, and matched skill name
    And then executes the skill normally
```

---

### Feature: Configuration Loading

```gherkin
Feature: Agent registry via agents.toml
  As a developer
  I want to register multiple agents in a single config file
  So that telos knows where each agent's skills and working directory live

  Scenario: Config loads from XDG standard location
    Given a file exists at ~/.config/telos/agents.toml
    When the CLI starts
    Then it loads agent definitions from that file

  Scenario: Config falls back to project root during development
    Given no file exists at ~/.config/telos/agents.toml
    And a file exists at {project_root}/config/agents.toml
    When the CLI starts
    Then it loads agent definitions from the project root config

  Scenario: No config file exists anywhere
    Given no agents.toml exists at any known location
    When the CLI starts
    Then it prints "No agents.toml found. Run `telos init` to create one."
    And exits with a non-zero status code

  Scenario: Linked agent loads skills from absolute path
    Given the kairos agent has mode "linked"
    And skills_dir is "~/Documents/ObsidianVault/.claude/commands"
    When the CLI loads the kairos agent
    Then it reads skills directly from the expanded absolute path

  Scenario: Installed agent loads skills from managed location
    Given the hackernews agent has mode "installed"
    When the CLI loads the hackernews agent
    Then it reads skills from ~/.local/share/telos/agents/hackernews/skills/

  Scenario: Installed agent auto-detects MCP config
    Given the clickup agent has mode "installed"
    And ~/.local/share/telos/agents/clickup/mcp.json exists
    When the CLI loads the clickup agent
    Then it sets mcp_config to the detected mcp.json path

  Scenario: Default agent used when no --agent flag provided
    Given agents.toml contains default_agent = "kairos"
    When I run `telos "run daily kickoff"` with no --agent flag
    Then the CLI uses the kairos agent
```

---

### Feature: Skill Discovery

```gherkin
Feature: Skill discovery from SKILL.md subdirectories
  As a developer
  I want the CLI to discover skills automatically from subdirectories
  So that I do not have to manually register each skill

  Scenario: All SKILL.md files in subdirectories are registered
    Given the kairos skills_dir contains:
      | kickoff/SKILL.md         |
      | shutdown/SKILL.md        |
      | interstitial/SKILL.md    |
      | weekly-summary/SKILL.md  |
      | weekly-review/SKILL.md   |
      | weekly-plan/SKILL.md     |
      | monthly-summary/SKILL.md |
    When the CLI loads the kairos agent
    Then all 7 skills are registered and available for routing
    And each skill's name is the subdirectory name

  Scenario: Description is extracted from YAML frontmatter
    Given a SKILL.md file contains:
      """
      ---
      description: Quick morning orientation. Surface what matters, set focus.
      ---
      # Kickoff
      """
    When the skill is loaded
    Then its description is "Quick morning orientation. Surface what matters, set focus."

  Scenario: Skill with missing description is loaded gracefully
    Given a subdirectory "experimental/SKILL.md" has no description field
    When the CLI loads the agent
    Then "experimental" is registered with description "(no description)"

  Scenario: List skills in table format
    When I run `telos list-skills --agent kairos`
    Then the CLI prints a table with columns: Skill, Description
    Sorted alphabetically by skill name

  Scenario: List all agents
    When I run `telos agents`
    Then the CLI prints a table with columns: Agent, Mode, Skills, Working Dir
```

---

### Feature: Intent Routing

```gherkin
Feature: Intent routing to skills
  As a developer
  I want natural language input to be routed to the correct skill
  So that I do not need to remember exact skill names

  Scenario: Exact skill name in input matches without API call
    Given the kairos agent has a skill named "kickoff"
    When I run `telos "kickoff"`
    Then the CLI matches via keyword pass
    And does not make an Anthropic API call

  Scenario: Partial phrase matches skill name without API call
    Given the kairos agent has a skill named "kickoff"
    When I run `telos "run daily kickoff"`
    Then the CLI detects "kickoff" in the input
    And matches via keyword pass

  Scenario: Longest match wins
    Given skills named "weekly" and "weekly-summary" exist
    When I run `telos "weekly-summary"`
    Then "weekly-summary" is matched, not "weekly"

  Scenario: Natural language routes via Claude API
    Given ANTHROPIC_API_KEY is set
    When I run `telos "let's wrap up for the day"`
    Then the CLI sends a routing request to claude-sonnet-4-6
    With max_tokens: 64
    And the response is used to route to the matching skill

  Scenario: ANTHROPIC_API_KEY not set falls back to keyword-only
    Given ANTHROPIC_API_KEY is not set
    When I run `telos "let's wrap up for the day"`
    Then the CLI attempts keyword matching only
    And if no match is found, prints available skills
```

---

### Feature: Skill Execution

```gherkin
Feature: Skill execution via Provider API
  As a developer
  I want matched skills to execute via direct LLM API calls
  So that execution is fast, provider-agnostic, and tool-capable

  Scenario: Skill executes with Anthropic provider
    Given TELOS_PROVIDER is "anthropic" (or unset)
    When a skill executes
    Then AnthropicProvider streams the response via the anthropic SDK
    And text tokens are printed to stdout in real time

  Scenario: Skill executes with Ollama provider
    Given TELOS_PROVIDER is "ollama"
    When a skill executes
    Then OllamaProvider streams via the OpenAI-compatible API
    And message format is translated from Anthropic to OpenAI internally

  Scenario: Built-in tools are available
    When any skill executes
    Then the model can call write_file, read_file, list_directory, fetch_url
    And file paths resolve relative to the agent's working_dir

  Scenario: Tool-use loop runs until completion
    When the model returns tool_call events
    Then telos executes each tool and returns results
    And the model continues generating
    And this repeats for up to 20 rounds

  Scenario: MCP tools are available when mcp.json is configured
    Given the clickup agent has an mcp.json
    When the standup skill executes
    Then MCP tools from the configured servers are available
    And built-in tools are also available alongside MCP tools

  Scenario: Prompt includes timestamp
    When any skill executes
    Then the prompt includes "Current date/time: YYYY-MM-DD HH:MM:SS TZ"

  Scenario: User request is appended to prompt
    When the user runs `telos "run kickoff and focus on the API refactor"`
    Then the skill body is the base prompt
    And "User request: run kickoff and focus on the API refactor" is appended

  Scenario: .env file is loaded into execution environment
    Given ~/.config/telos/.env contains ANTHROPIC_API_KEY=xxxx
    When any skill executes
    Then the .env values are loaded for provider creation and MCP headers

  Scenario: Execution is logged to JSONL
    When any skill executes
    Then skill_start, tool_call, and skill_end events are written
    To ~/.local/share/telos/logs/YYYY-MM-DD.jsonl

  Scenario: Execution errors are logged
    Given the provider raises an exception
    Then a skill_end event is logged with the error message
    And the exception is re-raised
```

---

### Feature: Agent Pack Installation

```gherkin
Feature: Install and manage agent packs
  As a developer
  I want to install pre-built agent packs into telos
  So that I can add new agents without manual file management

  Scenario: Install agent pack from local directory
    Given a directory ./hackernews/ contains agent.toml and skills/*/SKILL.md
    When I run `telos install ./hackernews`
    Then the CLI reads agent.toml for metadata
    And copies SKILL.md files to ~/.local/share/telos/agents/hackernews/skills/
    And copies mcp.json if present
    And registers in ~/.local/share/telos/registry.toml
    And adds the agent stanza to ~/.config/telos/agents.toml
    And prints: "Installed agent 'hackernews' with 1 skills"

  Scenario: Uninstall removes agent cleanly
    Given the hackernews agent is installed
    When I run `telos uninstall hackernews`
    Then the CLI prompts for confirmation
    And deletes ~/.local/share/telos/agents/hackernews/
    And removes the config stanza and registry entry

  Scenario: Uninstall blocks on linked agents
    Given the kairos agent is in linked mode
    When I run `telos uninstall kairos`
    Then the CLI prints: "Agent 'kairos' is linked, not installed."
    And exits without changes

  Scenario: agent.toml missing from pack directory
    Given a directory has skills/ but no agent.toml
    When I run `telos install ./bad-pack`
    Then the CLI prints: "No agent.toml found — not a valid agent pack."
    And exits with a non-zero status code
```

---

### Feature: Interactive Mode

```gherkin
Feature: Interactive agent and skill selection
  As a user
  I want a guided interface when I don't know the exact command
  So that I can browse agents and skills

  Scenario: Launch interactive mode
    When I run `telos` with no arguments
    Then the CLI displays a numbered list of agents
    And prompts me to select one

  Scenario: Select agent then skill
    Given I selected the kairos agent
    Then the CLI displays a numbered list of kairos skills
    And prompts me to select one
    And offers dry-run (d) or execute (y)

  Scenario: Execute from interactive mode
    Given I selected the kickoff skill and confirmed with 'y'
    Then the skill executes normally via execute_skill()
```

---

## Implementation Notes

1. **Skill file convention** — Skills use `skills/<name>/SKILL.md` subdirectories,
   not flat `.md` files. The subdirectory name is the skill name.

2. **No subprocess** — Execution is direct API calls, not `claude` CLI subprocess.
   The `executor` field in agent.toml is vestigial and ignored.

3. **Provider protocol** — `stream_completion()` is a sync Generator. The async
   boundary exists only in MCP client connections.

4. **Message format** — Internal messages use Anthropic format (`tool_use`/
   `tool_result` content blocks). OllamaProvider translates to OpenAI format
   internally via `_convert_messages()`.

5. **Keyword matching** — longest skill name first to avoid partial collisions.

6. **Frontmatter parsing** — simple string split on `---` delimiters. No YAML
   library needed.

7. **Rich** is used for all CLI output. Raw `print()` should not appear.

8. **All path handling** uses `pathlib.Path`. Never string concatenation for paths.

9. **uv is the only package manager**. All install instructions use `uv sync`.

10. **TOML writing** — use `tomli_w`. Never string-concatenate TOML.

---

## Future Considerations

- **Optional agent.toml** — Make `agent.toml` optional in the installer. Infer name
  from directory, description from SKILL.md frontmatter, working_dir as `~/obsidian/telos/<name>/`.
  This enables direct install from ClawHub, OpenClaw, or bare SKILL.md folders.
- **Remote install sources** — `telos install clawhub:<slug>`,
  `telos install github:<user>/<repo>`, `telos install <url>`. Fetch the skill folder,
  auto-generate agent.toml if absent, install normally.
- **Additional providers** — Apple Foundation Models, OpenAI, etc. Just implement
  `stream_completion()`.
- **Cost tracking** — Parse token counts from provider responses, log to JSONL.
- **`telos skill add`** — Scaffold a new SKILL.md in a subdirectory.
- **Guided init** — Detect Obsidian vaults, offer bundled pack installation.
