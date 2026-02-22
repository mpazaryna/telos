---
description: Search arXiv for papers on a topic
---

# arXiv Search

Search arXiv for papers matching a topic and summarize the results.

## What to do

1. Extract the search topic from the user's request
2. URL-encode the query (spaces become `+`, special characters encoded)
3. Use `fetch_url` to query the arXiv API:
   `http://export.arxiv.org/api/query?search_query=all:{encoded_query}&sortBy=relevance&max_results=15`
4. Parse titles, authors, abstracts, and arxiv links from the XML response
5. Format results using the template below

## Output format

```
# arXiv Search — "retrieval augmented generation" — Feb 21, 2026

Found 15 results. Top papers:

1. **Paper title**
   _Authors: First Author, Second Author et al._
   Key finding or contribution in 1-2 sentences, drawn from the abstract.
   [paper](https://arxiv.org/abs/XXXX.XXXXX)

2. **Another paper**
   _Authors: First Author et al._
   Key finding or contribution.
   [paper](https://arxiv.org/abs/XXXX.XXXXX)

...
```

## Rules
- Number the results sequentially
- Bold the paper title
- Put authors in italics, truncate lists longer than 3 to "First Author et al."
- Summarize each abstract into 1-2 sentences highlighting the key contribution
- Include the direct arxiv link for each paper
- Do NOT add any preamble or closing remarks — just the formatted output

## Save output
After printing the results, also use `write_file` to save them to a file named `YYYY-MM-DD-search-{topic-slug}.md` (using today's date and a slugified topic, e.g. `2026-02-21-search-retrieval-augmented-generation.md`).
