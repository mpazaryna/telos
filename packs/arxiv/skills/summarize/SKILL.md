---
description: Summarize a specific arXiv paper in depth
---

# arXiv Summarize

Fetch a specific arXiv paper and produce a deep summary.

## What to do

1. Extract the paper ID from the user's request. Accept either:
   - A bare ID like `2501.12345`
   - A full URL like `https://arxiv.org/abs/2501.12345`
2. Use `fetch_url` to get the paper's abstract page:
   `https://arxiv.org/abs/{id}`
3. Also use `fetch_url` to get structured metadata from the API:
   `http://export.arxiv.org/api/query?id_list={id}`
4. Produce a deep summary using the template below

## Output format

```
# Paper Summary — 2501.12345

## Title
Full paper title here

## Authors
Full author list

## Problem
What problem does this paper address? Why does it matter? (2-3 sentences)

## Approach
What method or technique do the authors propose? (3-5 sentences)

## Key Results
- Main result or finding
- Secondary results
- Comparison to prior work if mentioned

## Significance
Why is this paper interesting or important? Who should read it? (2-3 sentences)

## Links
- [arXiv](https://arxiv.org/abs/2501.12345)
- [PDF](https://arxiv.org/pdf/2501.12345)
```

## Rules
- Extract the paper ID correctly — strip any version suffix (v1, v2) for the fetch, but include it in links if present
- The Problem, Approach, and Significance sections should be written in plain language, accessible to a technical reader who is not a specialist
- Key Results should be a bulleted list of concrete findings
- Do NOT hallucinate results — only report what is in the abstract and metadata
- Do NOT add any preamble or closing remarks — just the formatted output

## Save output
After printing the summary, also use `write_file` to save it to a file named `YYYY-MM-DD-summary-{paper-id}.md` (using today's date and the paper ID, e.g. `2026-02-21-summary-2501.12345.md`).
