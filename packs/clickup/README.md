# ClickUp Agent Pack

A telos agent pack that gives Claude Code read-only access to ClickUp via the [ClickUp MCP server](https://mcp.clickup.com). Ships one skill (`standup`) that pulls a project status summary.

## What's in the pack

```
packs/clickup/
  agent.toml       # agent metadata (name, description, executor)
  mcp.json         # MCP server config — passed to Claude Code at runtime
  skills/
    standup/
      SKILL.md     # skill prompt: project standup for PAB Chiro space
```

### How MCP config works

Claude Code supports `--mcp-config <path>` to load MCP servers for a single session. When telos installs this pack, it:

1. Copies `skills/*/SKILL.md` to `~/.local/share/telos/agents/clickup/skills/`
2. Copies `mcp.json` to `~/.local/share/telos/agents/clickup/mcp.json`
3. Registers the agent in `~/.config/telos/agents.toml`

At execution time, telos detects the installed `mcp.json` and passes `--mcp-config ~/.local/share/telos/agents/clickup/mcp.json` to the `claude` subprocess. This gives the spawned Claude Code session access to ClickUp tools without polluting your global `~/.claude/mcp.json`.

### Why this approach

- **Scoped, not global** — MCP servers are tied to the agent that needs them, not your entire Claude Code config
- **Auto-detected** — no extra config needed in `agents.toml`; the installer copies the file and the runtime finds it
- **Portable** — the pack is self-contained; anyone can install it with `telos install`

## Prerequisites

1. **Claude Code** installed and on your PATH (`npm install -g @anthropic-ai/claude-code`)
2. **telos** installed (`uv pip install -e .` from the repo root)
3. **ClickUp MCP auth** — the first time Claude Code connects to the ClickUp MCP server, it will prompt you to authenticate via OAuth in your browser. No API key needed in `.env`.

## Install

```bash
telos install packs/clickup
```

Verify:

```bash
telos agents               # should show "clickup" in the table
telos list-skills --agent clickup  # should show "standup"
```

## Usage

### Dry run (no execution)

```bash
telos --agent clickup --dry-run "standup"
```

This routes the request and prints the matched skill without invoking Claude Code.

### Live run

```bash
telos --agent clickup "standup"
```

This spawns Claude Code with the ClickUp MCP server connected. Claude reads active tasks from the PAB Chiro space and prints a standup summary (in-progress, up next, blockers).

### Verbose mode

```bash
telos --agent clickup --verbose --dry-run "standup"
```

Prints routing details (agent name, skills dir, matched skill) before the result.

## Running the tests

From the repo root:

```bash
# all tests (unit + integration + e2e)
uv run pytest --tb=short -q

# only MCP-related tests
uv run pytest -k "mcp" -v

# unit tests for the MCP plumbing
uv run pytest tests/unit/test_config.py -k "mcp" -v
uv run pytest tests/unit/test_executor.py -k "mcp" -v
uv run pytest tests/unit/test_installer.py -k "mcp" -v

# integration test (full pipeline with --mcp-config flag)
uv run pytest tests/integration/test_pipeline.py -k "mcp" -v

# e2e test (install pack, verify mcp.json copied, dry-run routes)
uv run pytest tests/e2e/test_cli.py -k "mcp" -v
```

All MCP tests run offline — they don't call the real ClickUp API or require authentication.

## Uninstall

```bash
telos uninstall clickup
```

This removes the agent's skills directory (including `mcp.json`), the registry entry, and the `agents.toml` stanza.
