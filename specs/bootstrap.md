# telos CLI — Formal Build Specification

**Version:** 2.0
**Date:** 2026-02-20
**CLI Name:** `telos`
**Status:** Approved for Implementation

---

## Purpose

Build a lightweight Python CLI called `telos` that acts as a personal agent runtime.
It accepts natural language input, routes intent to the correct skill for the correct
agent, and executes that skill via Claude Code — from anywhere on the filesystem.

This replaces the need to `cd` into a specific directory and invoke Claude Code slash
commands manually. The user speaks naturally; the CLI handles routing and execution.

---

## Core Concepts

### Agent
A named profile representing a domain of work. Each agent has:
- A **skills directory** containing `.md` skill files
- A **working directory** where Claude Code is invoked
- A **mode**: `linked` (reads live from an external directory, e.g. Obsidian vault) or
  `installed` (skills managed by telos in `~/.local/share/telos/agents/`)

### Skill
A markdown file with YAML frontmatter containing a `description:` field and a prompt
body. The description is used for intent routing. The body is passed to Claude Code
for execution.

### Intent Routing
Two-pass process:
1. **Keyword match** — if the input contains an exact skill filename (e.g. `kickoff`),
   match directly with no API call.
2. **Claude API match** — if no keyword match, send the skill manifest + user input to
   `claude-sonnet-4-6` with `max_tokens: 64` to get the skill name. Requires
   `ANTHROPIC_API_KEY` in environment.

### Execution
Skills are executed by shelling out to the `claude` CLI (Claude Code), with `cwd` set
to the agent's `working_dir`. Claude Code authenticates via the user's existing Max
subscription OAuth. No new auth setup required.

---

## Agent Modes

### Linked Mode
For agents backed by an external directory the user actively edits (e.g. an Obsidian
vault). Skills are read live on every invocation — no sync, no cache, no install step.
Editing a skill file in the source directory is immediately reflected in telos.

Use linked mode when:
- Skills live in a repo or vault the user edits directly
- Live iteration matters more than version control
- The external directory has its own structure that shouldn't be duplicated

### Installed Mode
For agents whose skills are managed by telos. Skills are installed to
`~/.local/share/telos/agents/{agent-name}/skills/` via the `telos install` command.
This decouples the skill source (Agentic Factory, a git repo, a marketplace) from the
runtime.

Use installed mode when:
- Skills come from an external source (npm-style install, git repo, local package)
- The user doesn't need to live-edit the skill files
- Portability and reproducibility matter

---

## Install Model

### Skill Package Format
A skill package is a directory containing:
```
my-agent-pack/
├── agent.toml          # agent metadata (name, description, working_dir)
├── skills/
│   ├── check-email.md
│   ├── send-reply.md
│   └── triage.md
```

The `agent.toml` manifest:
```toml
name = "gmail"
description = "Gmail query and triage"
working_dir = "."
executor = "claude_code"
```

When installed, telos sets `mode = "installed"` automatically. The `executor` field
defaults to `"claude_code"` if omitted.

When `working_dir` is `"."`, telos uses the current working directory at invocation
time. When it's an absolute path, that path is used regardless of where telos is called.

### Install Locations

| Path | Purpose |
|------|---------|
| `~/.config/telos/` | Configuration (agents.toml, .env) |
| `~/.local/share/telos/agents/{name}/skills/` | Installed agent skill files |
| `~/.local/share/telos/registry.toml` | Tracks installed agents and versions |

### Install Sources (v1)

```bash
telos install ./path/to/agent-pack     # local directory
telos install gh:user/repo             # GitHub repo (future)
telos install marketplace:gmail-pro    # marketplace registry (future)
```

For v1, only local directory install is required. GitHub and marketplace sources are
reserved for future versions.

### Install Behavior

When `telos install ./my-agent-pack` is run:
1. Read `agent.toml` from the source directory
2. Copy skill `.md` files to `~/.local/share/telos/agents/{name}/skills/`
3. Register the agent in `~/.local/share/telos/registry.toml`
4. Merge agent config into `~/.config/telos/agents.toml`
5. Print summary: agent name, skill count, install path

If the agent already exists, prompt for confirmation before overwriting.

### Uninstall

```bash
telos uninstall gmail
```

Removes the agent's skill directory from `~/.local/share/telos/agents/` and its
stanza from `agents.toml`. Prompts for confirmation.

---

## Three Initial Agents

| Agent    | Mode      | Description                                      |
|----------|-----------|--------------------------------------------------|
| kairos   | linked    | Personal productivity — daily notes, weekly/monthly summaries, load tracking. Skills live in Obsidian vault at `.claude/commands/`. |
| gmail    | installed | Gmail query and triage. Skills managed by telos. |
| clickup  | installed | ClickUp task review and status. Skills managed by telos. |

---

## Technology Stack

| Concern              | Choice                        |
|----------------------|-------------------------------|
| Language             | Python 3.12+                  |
| Package management   | `uv`                          |
| CLI framework        | `typer`                       |
| Terminal output      | `rich`                        |
| TOML parsing         | `tomllib` (stdlib 3.11+)      |
| TOML writing         | `tomli_w`                     |
| API routing calls    | `anthropic` SDK               |
| Skill execution      | `subprocess` → `claude` CLI   |
| Config location      | `~/.config/telos/`            |
| Data location        | `~/.local/share/telos/`       |

---

## Project Structure

```
telos/
├── pyproject.toml
├── uv.lock
├── README.md
├── config/
│   └── agents.toml.example        # committed example; real config at ~/.config/telos/
├── packs/                          # bundled agent packs for install
│   ├── gmail/
│   │   ├── agent.toml
│   │   └── skills/
│   │       └── check-email.md
│   └── clickup/
│       ├── agent.toml
│       └── skills/
│           └── task-review.md
└── src/
    └── telos/
        ├── __init__.py
        ├── main.py                # Typer app, all CLI commands
        ├── config.py              # agents.toml loading and Agent dataclass
        ├── router.py              # skill discovery and intent routing
        ├── executor.py            # Claude Code subprocess execution
        └── installer.py           # agent pack install/uninstall logic
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
]

[project.scripts]
telos = "telos.main:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Install for development:
```bash
uv sync
uv run telos --help
```

Install globally:
```bash
uv tool install .
telos --help
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
description = "Personal productivity system — daily notes, weekly/monthly summaries, load tracking"
skills_dir  = "~/Documents/ObsidianVault/.claude/commands"
working_dir = "~/Documents/ObsidianVault"
executor    = "claude_code"

[agents.gmail]
mode        = "installed"
description = "Gmail query and triage"
# skills_dir is implicit: ~/.local/share/telos/agents/gmail/skills/
working_dir = "."
executor    = "claude_code"

[agents.clickup]
mode        = "installed"
description = "ClickUp task review and project status"
# skills_dir is implicit: ~/.local/share/telos/agents/clickup/skills/
working_dir = "."
executor    = "claude_code"
```

**Field definitions:**
- `mode`: `"linked"` reads from an explicit `skills_dir` path; `"installed"` reads
  from `~/.local/share/telos/agents/{name}/skills/`.
- `skills_dir`: Required for linked agents. Ignored for installed agents (path is
  derived from the agent name).
- `working_dir`: Directory Claude Code is invoked from. For `linked` agents, this
  must be the vault root so relative paths in skills resolve. For `installed` agents,
  `"."` resolves to the user's current working directory at invocation time.
- `executor`: Always `"claude_code"` in v1. Reserved for future extensibility.

---

## Skill File Format

Every skill file must have YAML frontmatter with a `description` field:

```markdown
---
description: Quick morning orientation. Surface what matters, set focus.
---

# Kickoff

[full skill prompt body here]
```

Skills without `description` frontmatter are registered with a warning and description
`"(no description)"`.

---

## Environment Variables

| Variable          | Required | Purpose                                              |
|-------------------|----------|------------------------------------------------------|
| `ANTHROPIC_API_KEY` | No     | Enables Claude API intent routing (Pass 2). Without it, keyword-only routing (Pass 1). |
| `CLICKUP_API_KEY`   | No     | Required by clickup agent skills at execution time.  |

Optional `.env` file at `~/.config/telos/.env` is loaded into every subprocess
environment before Claude Code is invoked.

---

## CLI Commands

### Core
```
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

### Agent & Skill Management
```
telos install <path>                 # install agent pack from local directory
telos uninstall <agent-name>         # remove installed agent and its skills
telos skill add --agent <name> <skill-name>  # add a starter skill file
```

### Setup
```
telos init                           # create starter config at ~/.config/telos/
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

  Scenario: Invoke default agent with natural language
    Given the CLI is installed and configured
    And the default agent is "kairos"
    When I run `telos "run daily kickoff"`
    Then the CLI routes the intent to the kairos agent
    And executes the "kickoff" skill in the kairos working directory
    And output streams to the terminal interactively

  Scenario: Invoke a specific agent explicitly
    Given agents "kairos", "gmail", and "clickup" are registered
    When I run `telos --agent gmail "any new email from Mila"`
    Then the CLI routes the intent to the gmail agent
    And executes the matching gmail skill

  Scenario: Whispr voice dictation passes through unchanged
    Given Whispr is configured to type dictated text into the active terminal
    When I dictate "write an interstitial on the chiro call with John"
    Then the shell receives `telos "write an interstitial on the chiro call with John"`
    And the CLI routes and executes correctly without any special handling

  Scenario: No matching skill found
    Given the kairos agent has skills: kickoff, shutdown, interstitial, weekly-summary, weekly-review, weekly-plan, monthly-summary
    When I run `telos "order me a pizza"`
    Then the CLI prints "No matching skill found for: 'order me a pizza'"
    And lists available skills for the default agent
    And exits with a non-zero status code

  Scenario: Dry run shows matched skill without executing
    When I run `telos --dry-run "run daily kickoff"`
    Then the CLI prints the matched agent name and skill name
    And does not invoke Claude Code
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
    And does not copy or cache those files

  Scenario: Installed agent loads skills from managed location
    Given the gmail agent has mode "installed"
    When the CLI loads the gmail agent
    Then it reads skills from ~/.local/share/telos/agents/gmail/skills/

  Scenario: Default agent used when no --agent flag provided
    Given agents.toml contains default_agent = "kairos"
    When I run `telos "run daily kickoff"` with no --agent flag
    Then the CLI uses the kairos agent
```

---

### Feature: Skill Discovery

```gherkin
Feature: Skill discovery from skills directory
  As a developer
  I want the CLI to discover skills automatically from markdown files
  So that I do not have to manually register each skill

  Scenario: All .md files in skills_dir are registered as skills
    Given the kairos skills_dir contains:
      | kickoff.md         |
      | shutdown.md        |
      | interstitial.md    |
      | weekly-summary.md  |
      | weekly-review.md   |
      | weekly-plan.md     |
      | monthly-summary.md |
    When the CLI loads the kairos agent
    Then all 7 skills are registered and available for routing

  Scenario: Description is extracted from YAML frontmatter
    Given a skill file contains:
      """
      ---
      description: Quick morning orientation. Surface what matters, set focus.
      ---
      # Kickoff
      """
    When the skill is loaded
    Then its description is "Quick morning orientation. Surface what matters, set focus."

  Scenario: Skill with missing description frontmatter is loaded with warning
    Given a file "experimental.md" exists in skills_dir with no description field
    When the CLI loads the agent
    Then "experimental" is registered with description "(no description)"
    And the CLI prints: "Warning: skill 'experimental' has no description — routing accuracy may be reduced"

  Scenario: Non-.md files in skills_dir are ignored
    Given skills_dir contains "kickoff.md" and "README.txt" and ".DS_Store"
    When the CLI loads the agent
    Then only "kickoff" is registered as a skill

  Scenario: List skills for an agent in table format
    When I run `telos list-skills --agent kairos`
    Then the CLI prints a table with columns: Skill, Description
    With one row per registered skill
    Sorted alphabetically by skill name

  Scenario: List all agents
    When I run `telos agents`
    Then the CLI prints a table with columns: Agent, Mode, Skills, Working Dir
    With one row per registered agent
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
    And routes to the kickoff skill

  Scenario: Partial phrase matches skill name without API call
    Given the kairos agent has a skill named "kickoff"
    When I run `telos "run daily kickoff"`
    Then the CLI detects "kickoff" in the input
    And matches via keyword pass without an API call

  Scenario: Natural language routes via Claude API
    Given ANTHROPIC_API_KEY is set in the environment
    And the kairos agent has skills with descriptions
    When I run `telos "let's wrap up for the day"`
    Then the CLI sends a routing request to claude-sonnet-4-6
    With a system prompt instructing it to return only a skill name or NONE
    And the request body contains the skill manifest and user input
    And max_tokens is 64
    And the response "shutdown" is used to route to the shutdown skill

  Scenario: Claude API returns NONE for unmatched input
    Given ANTHROPIC_API_KEY is set
    When the routing API call returns "NONE"
    Then the CLI prints "No matching skill found for: '<input>'"
    And lists available skills
    And exits with a non-zero status code

  Scenario: ANTHROPIC_API_KEY not set falls back to keyword-only routing
    Given ANTHROPIC_API_KEY is not set in the environment
    When I run `telos "let's wrap up for the day"`
    Then the CLI attempts keyword matching only
    And if no keyword match is found, prints available skills
    And exits with a non-zero status code

  Scenario: Routing system prompt instructs single-word response
    When a routing API call is made
    Then the system prompt contains instructions to respond with ONLY the skill name
    And nothing else — no explanation, no punctuation, no preamble
```

---

### Feature: Skill Execution

```gherkin
Feature: Skill execution via Claude Code
  As a developer
  I want matched skills to execute via Claude Code
  So that my Max subscription is used and vault file paths resolve correctly

  Scenario: Claude Code is invoked with correct working directory
    Given the kairos agent working_dir is ~/Documents/ObsidianVault
    When the kickoff skill executes
    Then Claude Code is invoked with cwd set to ~/Documents/ObsidianVault
    So that relative paths in the skill prompt resolve correctly

  Scenario: Skill prompt body is passed to Claude Code
    Given the kickoff skill file contains a prompt body after the frontmatter
    When the skill executes
    Then the full prompt body (excluding frontmatter) is passed to Claude Code
    As the -p / --print argument

  Scenario: Conversational skill stays interactive
    Given the kickoff skill contains "What's your focus today?"
    When the skill executes
    Then Claude Code runs interactively with stdin and stdout connected to the terminal
    And the session remains open until Claude Code completes

  Scenario: Pipeline skill runs to completion without interaction
    Given the weekly-summary skill requires no user input
    When the skill executes
    Then Claude Code runs to completion
    And all output streams to the terminal
    And the CLI exits cleanly when Claude Code finishes

  Scenario: .env file is loaded into subprocess environment
    Given ~/.config/telos/.env contains CLICKUP_API_KEY=xxxx
    When any skill executes
    Then the .env file contents are merged into the subprocess environment
    Before Claude Code is invoked

  Scenario: Claude Code binary not found on PATH
    Given the `claude` binary is not on the system PATH
    When any skill attempts to execute
    Then the CLI prints: "Claude Code not found. Install with: npm install -g @anthropic-ai/claude-code"
    And exits with a non-zero status code

  Scenario: Claude Code exits with non-zero status code
    Given Claude Code encounters an error during execution
    Then the CLI prints: "Claude Code exited with code <N>"
    And exits with the same non-zero status code
```

---

### Feature: Linked Mode — Kairos

```gherkin
Feature: Kairos agent linked to Obsidian vault
  As a developer using Kairos
  I want the CLI to read skills directly from my Obsidian vault
  So that editing skills in Obsidian is immediately reflected in the CLI

  Scenario: Kairos skills are read live on every invocation
    Given the kairos agent is in linked mode
    And I edit kickoff.md in my Obsidian vault
    When I next run `telos "run daily kickoff"`
    Then the CLI reads the updated skill file
    With no sync, cache, or reload step required

  Scenario: Vault path is read from agents.toml not hardcoded
    Given agents.toml contains skills_dir = "~/Documents/MyVault/.claude/commands"
    And agents.toml contains working_dir = "~/Documents/MyVault"
    When the CLI loads kairos
    Then it uses the configured working_dir as the Claude Code cwd
    And reads skills from the configured skills_dir

  Scenario: Vault path does not exist on filesystem
    Given the skills_dir path in agents.toml does not exist
    When the CLI loads the agent
    Then it prints: "Skills directory not found: <path>"
    And prints: "Check the skills_dir value in ~/.config/telos/agents.toml"
    And exits with a non-zero status code
```

---

### Feature: Agent Pack Installation

```gherkin
Feature: Install and manage agent packs
  As a developer
  I want to install pre-built agent packs into telos
  So that I can add new agents without manual file management

  Scenario: Install agent pack from local directory
    Given a directory ./gmail-pack/ contains agent.toml and skills/*.md
    When I run `telos install ./gmail-pack`
    Then the CLI reads agent.toml for agent metadata
    And copies skill files to ~/.local/share/telos/agents/gmail/skills/
    And registers the agent in ~/.local/share/telos/registry.toml
    And adds the agent stanza to ~/.config/telos/agents.toml
    And prints: "Installed agent 'gmail' with 3 skills"

  Scenario: Install overwrites existing agent with confirmation
    Given the gmail agent is already installed
    When I run `telos install ./gmail-pack-v2`
    Then the CLI prints: "Agent 'gmail' is already installed. Overwrite? [y/N]"
    And if confirmed, replaces the existing skills and updates config
    And if denied, exits without changes

  Scenario: Install from bundled packs directory
    Given the telos project includes packs/gmail/ and packs/clickup/
    When I run `telos install ./packs/gmail`
    Then the agent is installed from the bundled pack

  Scenario: Uninstall removes agent cleanly
    Given the gmail agent is installed
    When I run `telos uninstall gmail`
    Then the CLI prints: "Remove agent 'gmail' and all its skills? [y/N]"
    And if confirmed, deletes ~/.local/share/telos/agents/gmail/
    And removes the gmail stanza from agents.toml
    And prints: "Uninstalled agent 'gmail'"

  Scenario: Uninstall blocks on linked agents
    Given the kairos agent is in linked mode
    When I run `telos uninstall kairos`
    Then the CLI prints: "Agent 'kairos' is linked, not installed. Remove it from agents.toml manually."
    And exits without changes

  Scenario: List installed agents with install metadata
    When I run `telos agents`
    Then the table includes columns: Agent, Mode, Skills, Working Dir
    And installed agents show skill count from the managed directory
    And linked agents show skill count from the linked path

  Scenario: agent.toml missing from pack directory
    Given a directory ./bad-pack/ has skills/ but no agent.toml
    When I run `telos install ./bad-pack`
    Then the CLI prints: "No agent.toml found in ./bad-pack — not a valid agent pack."
    And exits with a non-zero status code
```

---

### Feature: Installed Mode — Gmail and ClickUp

```gherkin
Feature: Installed mode for managed agents
  As a developer adding a new agent
  I want telos to manage skill files in a standard location
  So that I don't need to track where files live

  Scenario: Installed agent skills live under ~/.local/share/telos/
    Given the gmail agent has mode "installed"
    When the CLI loads the gmail agent
    Then it reads skills from ~/.local/share/telos/agents/gmail/skills/

  Scenario: Add a skill to an installed agent
    When I run `telos skill add --agent gmail "send-reply"`
    Then the file ~/.local/share/telos/agents/gmail/skills/send-reply.md is created
    And it contains:
      """
      ---
      description: [brief description of what this skill does]
      ---

      # Send Reply

      [skill prompt here]
      """

  Scenario: ClickUp skill requires API key surfaced gracefully
    Given the clickup agent task-review skill uses CLICKUP_API_KEY
    And CLICKUP_API_KEY is not set in environment or .env
    When the skill executes
    Then Claude Code surfaces the missing credential in its output
    And the CLI additionally prints: "Tip: Add CLICKUP_API_KEY to ~/.config/telos/.env"
```

---

### Feature: Initialization

```gherkin
Feature: CLI initialization
  As a new user
  I want a guided init command
  So that I do not have to hand-edit TOML before first use

  Scenario: Init creates config and data directories
    Given ~/.config/telos/ does not exist
    When I run `telos init`
    Then the CLI creates ~/.config/telos/
    And creates ~/.config/telos/agents.toml with commented stanza templates
    And creates ~/.local/share/telos/agents/ directory
    And prints: "Config created at ~/.config/telos/agents.toml"
    And prints: "Edit it to register your agents, then run `telos agents` to verify."

  Scenario: Init detects Obsidian vault with .claude/commands and offers to add kairos
    Given ~/Documents/ObsidianVault/.claude/commands/ exists
    When I run `telos init`
    Then the CLI prints: "Found Obsidian vault at ~/Documents/ObsidianVault — add as kairos agent? [y/N]"
    And if confirmed, writes the kairos stanza to agents.toml

  Scenario: Init installs bundled packs if present
    Given the telos project includes packs/gmail/ and packs/clickup/
    When I run `telos init`
    Then the CLI offers to install each bundled pack
    And for each confirmed pack, runs the install flow

  Scenario: Init does not overwrite existing config
    Given ~/.config/telos/agents.toml already exists
    When I run `telos init`
    Then the CLI prints: "Config already exists at ~/.config/telos/agents.toml — not overwriting."
    And exits cleanly without modifying the file
```

---

## Implementation Notes for Claude Code

When implementing from this spec:

1. **Start with project scaffold** — `pyproject.toml`, directory structure, empty
   module files with docstrings.

2. **Build and test in this order:**
   - `config.py` — load agents.toml, parse Agent dataclass, handle missing file
   - `router.py` — skill discovery from .md files, keyword pass, API pass
   - `executor.py` — subprocess to `claude` CLI, .env loading, error handling
   - `installer.py` — agent pack install/uninstall, registry management
   - `main.py` — wire all commands with Typer

3. **Test each module independently** before wiring into the CLI.

4. **The kairos agent skills_dir must be configurable** — never hardcode a vault path.
   The user will set it in agents.toml.

5. **Keyword matching** uses `skill_name in user_input.lower()` across all registered
   skill names for the selected agent. Match on the longest skill name first to avoid
   partial collisions (e.g. `weekly-summary` before `weekly`).

6. **Frontmatter parsing** uses a simple string split on `---` delimiters — no YAML
   library needed. Extract only the `description:` field.

7. **Claude Code subprocess** must inherit the parent process's stdin/stdout/stderr
   so interactive skills work correctly. Do not use `capture_output=True`.

8. **Rich** is used for all CLI output (tables, panels, warnings). Raw `print()`
   should not appear in production code.

9. **All path handling** uses `pathlib.Path` throughout. Never string concatenation
   for paths.

10. **uv is the only package manager** — do not use pip or poetry. All install
    instructions use `uv sync` and `uv tool install`.

11. **Installed mode path derivation** — for installed agents, the skills directory
    is always `~/.local/share/telos/agents/{agent_name}/skills/`. This is derived
    from the agent name, never stored in config.

12. **TOML writing** — use `tomli_w` for writing to agents.toml and registry.toml.
    Never string-concatenate TOML.

13. **Registry tracking** — `~/.local/share/telos/registry.toml` tracks installed
    agents with metadata (install date, source path, skill count) for `telos agents`
    display and uninstall safety.

---

## Relationship to Agentic Factory

The [Agentic Factory](https://github.com/...) is a meta-generator system for building
Claude Code components. It produces skill files with YAML frontmatter and markdown
prompt bodies — the exact format telos consumes.

The workflow:
1. Use Agentic Factory to design and generate skills via guided `/build` workflows
2. Package the generated `SKILL.md` files into an agent pack with an `agent.toml`
3. Run `telos install ./my-agent-pack` to install them into the telos runtime
4. Invoke skills naturally: `telos "check my email"` or `telos --agent clickup "what's overdue"`

Agentic Factory is one source of agent packs. Others may include community repos,
marketplace registries, or hand-authored skill files. telos is source-agnostic — it
only cares about the skill file format and the agent pack structure.
