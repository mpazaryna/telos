---
description: Quick capture a timestamped note to log/ folder
---

# Interstitial

Fast capture for thoughts, notes, and observations throughout the day.

## Two Modes

### 1. Explicit Invocation (`/interstitial`)
When the user types `/interstitial` with no content:
- Prompt: "What's on your mind?"
- Wait for response, then save

### 2. Natural Language Capture
When the user dictates something that's clearly meant to be captured, save it immediately. Don't ask for clarification.

**Recognition patterns:**
- "log that as an interstitial"
- "capture that as a note"
- "please log that"
- "let's do an interstitial note about..."
- "interstitial note:"
- "quick note:"
- Any statement followed by a capture instruction

**Example:**
> "We figured out that the sync issue was caused by a race condition in the file watcher. Log that as an interstitial."

Just save it. Don't ask "what would you like to capture?"

## Create the Note

- Filename: `50-log/interstitial/YYYY-MM-DD-HHMMSS.md`
- Frontmatter:
  ```yaml
  ---
  tags: [interstitial]
  date: YYYY-MM-DD
  time: HH:MM
  ---
  ```
- Body: The captured text (extracted from what user said, minus the capture instruction)

## Confirm

Show: "Logged to `50-log/interstitial/YYYY-MM-DD-HHMMSS.md`"

Done - no follow-up needed.

## Notes

- No title needed - the timestamp is the identifier
- Tag with `interstitial` for easy filtering in Obsidian
- These are raw captures - process later or let them accumulate
- Can be reviewed during `/shutdown` or weekly review
- Works great with voice dictation (Wispr)
