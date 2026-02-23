# Skill example

This is what a skill looks like. A folder with a `SKILL.md` inside it.

```
frontpage/
  SKILL.md
```

That's it. The `SKILL.md` is the entire configuration — what to do, how to format the output, where to save it. No config files, no pipeline DSL. Open `frontpage/SKILL.md` and read it. It's a markdown file that tells the model to fetch the Hacker News RSS feed, group stories by theme, and write the result to a dated file.

A skill can also include companion scripts (shell, Python, whatever) if it needs them. This one doesn't.

Compatible with [OpenClaw](https://github.com/openclaw/skills) — same format, any runtime.
