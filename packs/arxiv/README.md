# arXiv Agent Pack

A telos agent pack for arXiv paper discovery — trending papers by category, topic search, and deep paper summaries. Uses the public arXiv API with no authentication required.

## What's in the pack

```
packs/arxiv/
  agent.toml       # agent metadata (name, description, working_dir)
  skills/
    trending/
      SKILL.md     # fetch recent papers from an arXiv category
    search/
      SKILL.md     # search papers by topic keyword
    summarize/
      SKILL.md     # deep summary of a specific paper by ID or URL
```

### How it works

All three skills use telos built-in tools only — `fetch_url` to hit the arXiv Atom API and `write_file` to save results. No scripts, no MCP servers, no authentication.

At execution time, telos routes natural language to a skill, builds the prompt from SKILL.md, and the model fetches from arXiv, parses XML, and writes formatted markdown output.

## Prerequisites

1. **telos** installed (`uv pip install -e .` from the repo root)
2. **ANTHROPIC_API_KEY** in `~/.config/telos/.env` (or use Ollama with `TELOS_PROVIDER=ollama`)

## Install

```bash
telos install packs/arxiv
```

Verify:

```bash
telos agents          # should show "arxiv" in the table
telos list-skills     # should show trending, search, summarize
```

## Usage

### Trending papers

Fetch the latest papers from an arXiv category, grouped by theme.

```bash
uv run telos --agent arxiv "trending"                # defaults to cs.AI
uv run telos --agent arxiv "trending in cs.CL"       # computational linguistics
telos --agent arxiv "trending in cs.LG"       # machine learning
telos --agent arxiv "trending in stat.ML"     # statistical ML
```

Output: `~/obsidian/telos/arxiv/YYYY-MM-DD-trending-{category}.md`

Common categories: `cs.AI`, `cs.LG`, `cs.CL`, `cs.CV`, `cs.SE`, `stat.ML`, `math.OC`

### Search papers

Search arXiv by topic and get a ranked summary of results.

```bash
telos --agent arxiv "search retrieval augmented generation"
telos --agent arxiv "search multi-agent reinforcement learning"
telos --agent arxiv "search code generation with LLMs"
```

Output: `~/obsidian/telos/arxiv/YYYY-MM-DD-search-{topic-slug}.md`

### Summarize a paper

Get a deep summary of a specific paper by ID or URL.

```bash
telos --agent arxiv "summarize 2501.12345"
telos --agent arxiv "summarize https://arxiv.org/abs/2501.12345"
```

Output: `~/obsidian/telos/arxiv/YYYY-MM-DD-summary-{paper-id}.md`

The summary includes: title, authors, problem statement, approach, key results, and significance.

### Dry run

Test routing without executing:

```bash
telos --dry-run --agent arxiv "trending"
telos --dry-run --agent arxiv "search transformers"
telos --dry-run --agent arxiv "summarize 2501.12345"
```

## Skills reference

| Skill | Description | API endpoint |
|-------|-------------|-------------|
| `trending` | Recent papers from a category, grouped by theme | `export.arxiv.org/api/query?search_query=cat:{category}` |
| `search` | Topic search with ranked results | `export.arxiv.org/api/query?search_query=all:{query}` |
| `summarize` | Deep summary of a single paper | `arxiv.org/abs/{id}` + API metadata |

## Uninstall

```bash
telos uninstall arxiv
```
