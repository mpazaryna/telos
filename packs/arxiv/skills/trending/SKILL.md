---
description: Fetch trending papers from an arXiv category
---

# arXiv Trending

Fetch recent papers from an arXiv category and summarize them grouped by theme.

## What to do

1. Determine the category from the user's request. Default to `cs.AI` if none specified.
   Common categories: `cs.AI`, `cs.LG`, `cs.CL`, `cs.CV`, `cs.SE`, `stat.ML`, `math.OC`
2. Use `fetch_url` to get the Atom feed:
   `http://export.arxiv.org/api/query?search_query=cat:{category}&sortBy=lastUpdatedDate&max_results=20`
3. Parse titles, authors, one-line summaries, and arxiv links from the XML response
4. Group papers by theme and format using the template below

## Output format

```
# arXiv Trending — cs.AI — Feb 21, 2026

## Reasoning & Planning

- **Paper title** — One-sentence summary of the contribution.
  _Authors: First Author, Second Author et al._ · [paper](https://arxiv.org/abs/XXXX.XXXXX)

- **Another paper** — Summary here.
  _Authors: First Author et al._ · [paper](https://arxiv.org/abs/XXXX.XXXXX)

## Agents & Tool Use

- ...

## Multimodal

- ...
```

## Rules
- Use `## Theme` headers — pick themes that naturally fit the papers (e.g., Reasoning & Planning, Agents & Tool Use, Multimodal, NLP, Vision, Safety & Alignment, Benchmarks, Theory, Applications)
- Bold the paper title, follow with an em dash and a one-sentence summary
- Put authors in italics on the next line, followed by the arxiv link
- Truncate author lists longer than 3 to "First Author et al."
- Order papers within each theme by relevance
- Do NOT add any preamble or closing remarks — just the formatted output

## Save output
After printing the summary, also use `write_file` to save it to a file named `YYYY-MM-DD-trending-{category}.md` (using today's date and the category, e.g. `2026-02-21-trending-cs.AI.md`).
