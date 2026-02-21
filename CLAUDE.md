# CLAUDE.md

## What is telos?

Telos is a clawbot — a runtime that executes claws (SKILL.md files). It is compatible
with the OpenClaw skill ecosystem and ClawHub registry. Unlike most clawbots that wrap
`claude -p`, telos calls the LLM API directly with its own tool-use loop and provider
abstraction.

## Key Architecture Decisions

- **SKILL.md is the universal contract.** A skill is a folder with a SKILL.md and
  optionally companion scripts. This format is shared across OpenClaw, ClawHub, and
  any clawbot. The runtime is interchangeable — the skill is the product.

- **agent.toml is scaffolding, not a requirement.** It exists to override defaults
  (working_dir, name, description) but the goal is to make it optional. A bare SKILL.md
  folder should be a valid installable unit. Name from directory, description from
  frontmatter, working_dir defaults to `~/telos/<name>/`.

- **Direct API, no subprocess.** Execution uses the anthropic SDK directly, not
  `claude -p`. This eliminates the 5-10s Node.js cold start per execution.

- **Provider protocol.** `stream_completion()` is a sync Generator yielding StreamEvents.
  AnthropicProvider and OllamaProvider implement it. Swap with `TELOS_PROVIDER` env var.

- **Built-in tools + MCP.** Five built-in tools (write_file, read_file, list_directory,
  fetch_url, run_command) are always available. MCP tools from mcp.json are merged
  alongside them. Tool dispatch routes by name.

- **Output convention.** Agents write to `~/telos/<agent-name>/` by default. Linked
  agents (kairos) override this to write to their own directory (Obsidian vault).

## Project Layout

```
src/telos/
  main.py           # CLI commands (typer)
  config.py         # agents.toml loading, Agent dataclass
  router.py         # skill discovery + intent routing
  executor.py       # execution engine, tool-use loops
  provider.py       # Provider protocol, Anthropic + Ollama
  mcp_client.py     # MCP SSE/HTTP client
  logger.py         # per-day JSONL logging
  installer.py      # pack install/uninstall + scripts copy
  interactive.py    # interactive agent/skill selection

packs/              # bundled agent packs
  kairos/           # personal productivity (linked to Obsidian)
  hackernews/       # HN frontpage summaries
  clickup/          # project standup via MCP
  apple-calendar/   # Calendar.app integration (ported from OpenClaw)

specs/
  bootstrap.md      # full build specification (v3.0)
```

## Conventions

- **Python 3.12+**, managed with `uv`. Run tests: `uv run pytest tests/ -q`
- **All paths** use `pathlib.Path`, never string concatenation.
- **TOML writing** uses `tomli_w`, never string concatenation.
- **Rich** for all CLI output. No raw `print()`.
- **Frontmatter parsing** is simple string split on `---`. No YAML library.
- **Keyword routing** matches longest skill name first to avoid collisions.
- **Logging** to `~/.local/share/telos/logs/YYYY-MM-DD.jsonl` — three event types:
  skill_start, tool_call, skill_end.

## Testing

```bash
uv run pytest tests/ -q          # all tests
uv run pytest tests/unit -q      # unit only
uv run pytest tests/integration  # integration (mocked providers)
```

## The Big Insight

The value used to be in the runtime — Oracle, Salesforce, Microsoft. You paid for
the engine and your logic was locked inside. Now a skill is a markdown file, the
model is an API call, and the runtime is interchangeable plumbing. The SKILL.md is
portable across any clawbot. The runtime is commoditized. The skill is the product.
