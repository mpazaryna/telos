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

Never seen a skill? Look at [`docs/skill-example/`](docs/skill-example/).

## Why it's built this way

The runtime used to be the moat. You paid Oracle for the database, Salesforce for the CRM, Microsoft for the BI layer. Your logic was locked inside their runtime. That was the business model.

Now a skill is a markdown file. The integrations are MCP servers anyone can stand up. The model is an API call. There's nothing left to lock in.

The value is in the skills — the accumulated knowledge of *how* to do something — and the models that interpret them. Everything in between is plumbing. Write a skill once, run it anywhere.

## Skills as personal assets

In the early 1990s a spreadsheet was a personal asset. You built it yourself, encoding domain knowledge into formulas nobody else had. The tool that ran it (Lotus 1-2-3, then Excel) was interchangeable. What mattered was the `.xls`.

Skills are the same pattern, one level up. A `SKILL.md` encodes domain expertise — how to summarize a frontpage, run a standup, triage a calendar — in a file any runtime can execute. You keep it in `~/.skills/`. You carry it between machines. The runtime is plumbing. The skill is the asset.

The difference is what sits between the file and the output. A spreadsheet had a formula engine. A skill has an LLM. The formulas were rigid — `=SUM(B2:B10)`. The instructions are natural language — *"fetch the RSS feed, group by theme, write a summary."* Same pattern: portable files, interchangeable engines. But the ceiling on what a single file can do is incomparably higher.

`~/.skills/` is a personal library — like `~/Documents` but for automation. Each skill compounds over time. Twenty skills for your domain is twenty reusable assets that work with any model, on any runtime, from any device.

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

Initialize:

```bash
uv run telos init
```

Agents live in `~/.skills/` and are discovered automatically. Override with `TELOS_SKILLS_DIR`.

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

## License

MIT
