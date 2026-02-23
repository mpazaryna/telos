---
description: Summarize the current Hacker News front page
---

# Hacker News Frontpage

Fetch and summarize the current Hacker News front page.

## What to do

1. Fetch the RSS feed from `https://hnrss.org/frontpage?count=30`
2. Parse the titles, links, points, comment counts, and descriptions from the feed
3. Summarize the top stories in the exact format below

## Output format

Start with a one-line date header, then group stories by theme.

```
# HN — Feb 21, 2026

## AI / ML

- **Story title** — One-sentence summary.
  _142 pts · 87 comments_ · [link](https://...)

- **Another story** — Summary here.
  _98 pts · 43 comments_ · [link](https://...)

## Systems / Infra

- **Story title** — Summary.
  _210 pts · 112 comments_ · [link](https://...)

## Show HN

- ...
```

## Rules
- Use `## Theme` headers — pick from: AI / ML, Systems / Infra, Programming, Show HN, Science, Startups / Business, Culture / Other
- Bold the story title, follow with an em dash and a one-sentence summary
- Put points, comments in italics on the next line, followed by the link
- Order stories within each theme by points descending
- Skip job posts, polls, and low-substance items
- Limit to the ~15 most interesting stories
- Do NOT add any preamble or closing remarks — just the formatted output

## Save output
After printing the summary, also write it to a file named `YYYY-MM-DD-frontpage.md` (using today's date).
