# CLAUDE.md

## What is telos?

Telos is a lightweight agent runtime. It executes skills (SKILL.md files) via direct
LLM API calls with a provider abstraction — same skills, any model (Anthropic, Ollama,
etc.). Compatible with the OpenClaw skill ecosystem. Surfaces via CLI, interactive
mode, or Discord bot.

## Key Architecture Decisions

- **SKILL.md is the contract.** A skill is a folder with a SKILL.md and optionally
  companion scripts. Compatible with OpenClaw and ClawHub. The runtime is
  interchangeable — the skill is the product.

- **`~/.skills/` is the canonical agent source.** All agent packs live in `~/.skills/`.
  Discovery scans this directory automatically. `agents.toml` exists for overrides only
  (working_dir, default agent). Override location with `TELOS_SKILLS_DIR` env var.

- **agent.toml is scaffolding, not a requirement.** It exists to override defaults
  (working_dir, name, description). A bare SKILL.md folder is a valid installable unit.
  Name from directory, description from frontmatter, working_dir defaults to
  `~/obsidian/telos/<name>/`.

- **Dual working directories.** File tools (write_file, read_file, list_directory)
  resolve relative to the agent's `working_dir` (Obsidian output). `run_command` uses
  `pack_dir` (the pack directory in `~/.skills/`) so companion scripts are found.

- **Direct API, no subprocess.** Execution uses LLM SDKs directly, not a CLI
  subprocess. No cold start overhead per execution.

- **Provider protocol.** `stream_completion()` is a sync Generator yielding StreamEvents.
  AnthropicProvider and OllamaProvider implement it. Swap with `TELOS_PROVIDER` env var.

- **Built-in tools + MCP.** Five built-in tools (write_file, read_file, list_directory,
  fetch_url, run_command) are always available. MCP tools from mcp.json are merged
  alongside them. Tool dispatch routes by name.

- **Output convention.** Agents write to `~/obsidian/telos/<agent-name>/` by default.
  All output lands in the Obsidian vault for search, backlinks, and mobile access.

## Project Layout

```
src/telos/
  main.py           # CLI commands (typer)
  config.py         # agent discovery from ~/.skills/ + agents.toml overrides
  router.py         # skill discovery + intent routing
  executor.py       # execution engine, tool-use loops, dual cwd
  provider.py       # Provider protocol, Anthropic + Ollama
  mcp_client.py     # MCP SSE/HTTP client
  logger.py         # per-day JSONL logging
  installer.py      # pack install/uninstall (copytree to ~/.skills/)
  interactive.py    # interactive agent/skill selection

docs/
  skill-example/    # annotated example of a SKILL.md

.orchestra/          # agentic reference docs
  specs/
    bootstrap.md    # full build specification (v3.0)
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
portable. The runtime is commoditized. The skill is the product.
