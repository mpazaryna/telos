# ADR-003: Agentic Factory as the Skill Authoring Tool

**Status:** Accepted
**Date:** 2026-02-22

## Context

Telos is a runtime — it executes SKILL.md files but has no opinion about how they get
written. Early skills were hand-authored: create a folder, write YAML frontmatter, write
the prompt body, add companion scripts. This works but requires knowing the format
conventions, and there's no validation until you try to run the skill.

Separately, the agentic-factory project (`~/agentic-factory`) exists as a meta-generator
for Claude Code components. It uses interactive Q&A workflows (4-11 guided questions)
backed by factory templates (5,175 lines of encoded best practices) to produce validated
skills, agents, commands, prompts, and hooks. The output format — a folder with a
SKILL.md, optional scripts, README, and samples — is the same contract telos consumes.

## Decision

Agentic-factory is the authoring tool; telos is the runtime. They are separate projects
with a shared contract: the SKILL.md folder.

The workflow is:

```
agentic-factory (/build) → SKILL.md folder → telos install → telos execute
```

Agentic-factory handles:
- Interactive skill creation via specialist guide agents
- YAML frontmatter validation and format enforcement
- Kebab-case naming, mandatory sections, file cleanliness
- Generation of companion files (README, HOW_TO_USE, samples, scripts)

Telos handles:
- Skill discovery and intent routing
- Provider-agnostic execution (Anthropic, Ollama)
- Built-in tools + MCP tool dispatch
- Output persistence and structured logging

Neither project depends on the other at the code level. The SKILL.md format is the
interface boundary.

## Consequences

- **Clean separation of concerns.** Authoring and execution are independent. You can
  write skills by hand, use agentic-factory, or use any other tool that produces the
  SKILL.md folder format.
- **Validation shifts left.** Factory templates catch format errors, missing frontmatter,
  and naming violations at authoring time rather than at execution time.
- **Ecosystem compatibility.** Agentic-factory currently targets Claude Code's
  `.claude/commands/` format, but the folder structure (SKILL.md + scripts) is identical
  to what telos, OpenClaw, and ClawHub expect. Skills authored in the factory are
  portable across runtimes.
- **No coupling.** Telos doesn't import or call agentic-factory. Agentic-factory doesn't
  know about telos's provider protocol or tool system. Changes to either project don't
  break the other as long as the SKILL.md contract holds.
- **Future opportunity.** A `telos create` command could invoke the factory workflow
  directly, but this is optional convenience — not a requirement.
