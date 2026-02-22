# ADR-002: Direct API Execution Over Subprocess

**Status:** Accepted
**Date:** 2026-02-01 (backfilled 2026-02-22)

## Context

Most clawbots execute skills by spawning a CLI subprocess — typically Claude Code via
`claude --skill ...`. This works but has costs:

- **Cold start.** Node.js process startup adds 5-10s per invocation.
- **Provider lock-in.** The subprocess dictates which model runs. You can't swap to
  Ollama or another provider without changing the entire execution path.
- **Opaque tool dispatch.** Tool calls go through the subprocess's own tool system.
  You can't add built-in tools or merge MCP tools alongside them.
- **No streaming control.** The parent process gets stdout from the child, but can't
  intercept tool calls, inject context, or log structured events mid-execution.

## Decision

Telos calls LLM provider SDKs directly — no subprocess, no CLI wrapper. Execution uses
a **Provider protocol** where `stream_completion()` is a sync Generator yielding
`StreamEvent` objects (`text`, `tool_call`, `done`).

Two providers implement the protocol:
- **AnthropicProvider** — uses the `anthropic` SDK with `client.messages.stream()`
- **OllamaProvider** — uses the `openai` SDK against Ollama's OpenAI-compatible endpoint

Provider selection is a single env var (`TELOS_PROVIDER=anthropic|ollama`).

The tool-use loop runs in-process: stream tokens to stdout, execute tool calls locally
(built-in) or via MCP (remote), append results, repeat up to 20 rounds.

## Consequences

- **No cold start.** Python process is already running; first API call goes out
  immediately.
- **Provider-agnostic.** Same skill, same execution path, different backend. Swap with
  one env var. Adding a new provider means implementing one method.
- **Full tool control.** Five built-in tools (write_file, read_file, list_directory,
  fetch_url, run_command) are always available. MCP tools merge alongside them. Tool
  dispatch routes by name — built-in or MCP, transparent to the skill.
- **Structured logging.** Because execution is in-process, we log skill_start,
  tool_call, and skill_end events to per-day JSONL with full context.
- **Message format translation.** Internal messages use Anthropic format. OllamaProvider
  translates to OpenAI format via `_convert_messages()`. This is contained complexity —
  each provider handles its own wire format.
- **Async boundary only at MCP.** The provider protocol is sync (Generator). The only
  async code is the MCP client connection. This keeps the core simple.
- **Engine stays small.** The entire runtime is under 1000 lines of Python. Auditable,
  forkable, disposable — consistent with the thesis that the runtime is commoditized.
