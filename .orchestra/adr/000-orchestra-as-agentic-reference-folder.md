# ADR-000: .orchestra as the Agentic Reference Folder

**Status:** Accepted
**Date:** 2026-02-22

## Context

As the project matured, documentation accumulated that serves a specific audience:
agentic tools (Claude Code, telos itself, future automation). Build specs, architectural
decision records, design rationale — these aren't user-facing docs (README, inline
comments) and they aren't code. They're reference material that an agent consumes to
understand the project before making changes.

This kind of documentation was initially scattered — `specs/bootstrap.md` at the project
root, decisions captured only in CLAUDE.md, context split across memory files. There was
no single place an agent (or a human reviewing agent context) could go to find the
authoritative project knowledge.

## Decision

Create a `.orchestra/` directory at the project root as the canonical home for agentic
reference documentation. Current structure:

```
.orchestra/
├── adr/           # architectural decision records
└── specs/         # build specifications
```

The name "orchestra" reflects the coordination role — it's where the score lives, not
where the instruments play. The dot-prefix signals it's project metadata, not source
code or user-facing content.

## Consequences

- **Single source of truth for agents.** CLAUDE.md stays concise (project context +
  conventions). `.orchestra/` holds the deep reference material — specs, ADRs, and
  whatever else agents need to make informed decisions.
- **Checked into the repo.** Unlike memory files (per-user, in `~/.claude/`), orchestra
  docs are shared with anyone who clones the project. A new contributor — human or
  agent — gets the full decision history.
- **Extensible.** Additional subdirectories can be added as needs arise (e.g.,
  `runbooks/`, `context/`, `decisions/`) without polluting the project root.
- **Dot-prefix keeps it out of the way.** Doesn't clutter `ls` output or confuse users
  looking for source code. Visible when you need it, invisible when you don't.
- **Not coupled to any tool.** The folder is plain markdown files. Any agent, any IDE,
  any tool can read it. No proprietary format.
