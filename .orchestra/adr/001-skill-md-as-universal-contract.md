# ADR-001: SKILL.md as the Universal Skill Contract

**Status:** Accepted
**Date:** 2026-02-01 (backfilled 2026-02-22)

## Context

We needed a format for defining what an agent skill does — the prompt, the metadata,
the tools it expects. The options ranged from code-based definitions (Python classes,
YAML pipelines, JSON configs) to something simpler.

The OpenClaw ecosystem had already converged on a convention: a folder with a `SKILL.md`
file containing YAML frontmatter (`description:`) and a markdown prompt body. Skills
from ClawHub, OpenClaw, and community contributors all use this format.

## Decision

A **skill is a folder with a `SKILL.md`** and optionally companion scripts. The SKILL.md
is the entire configuration — no separate config files, no pipeline DSL, no code. The
frontmatter carries metadata (description for routing), the body is the prompt sent to
the LLM.

```
apple-calendar/
  SKILL.md
  scripts/
    cal-list.sh
    cal-create.sh
```

This format is the shared contract across OpenClaw, ClawHub, and any clawbot runtime.
Telos adopts it as-is rather than inventing its own.

## Consequences

- **Portability.** A skill written for any clawbot works in telos without modification.
  We ported apple-calendar from OpenClaw in minutes.
- **No lock-in.** Skills are human-readable markdown. Nothing proprietary, nothing
  compiled, nothing that ties you to a specific runtime.
- **Simple parsing.** Frontmatter is a string split on `---` delimiters — no YAML
  library needed. The body is passed through verbatim.
- **agent.toml becomes scaffolding.** Since the skill itself is self-describing, the
  wrapper config (`agent.toml`) only exists for overrides (working_dir, grouping).
  The goal is to make it optional entirely.
- **Routing from description.** The `description` frontmatter field powers both keyword
  matching and API-based intent routing. Skills without it get `"(no description)"`.
- **Runtime commoditized.** If the skill format is shared and portable, the runtime is
  interchangeable plumbing. The value is in the skill (accumulated knowledge of *how*
  to do something) and the model (intelligence), not the engine.
