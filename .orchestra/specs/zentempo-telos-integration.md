# Spec: Zentempo + Telos Integration

> Expand zentempo from a pomodoro timer into a personal command center menubar app
> with a telos skill browser and launcher.

## Problem

As the number of telos skills grows, you lose cognitive awareness of what's available.
`telos list-skills` in a terminal table is functional but not discoverable — you have
to already know what you're looking for. A menubar GUI solves the "what do I have?"
problem while keeping execution one click away.

## Why zentempo

Zentempo is already a production macOS menubar app (SwiftUI, NSPopover, LSUIElement).
The architecture is clean — `PomodoroTimer` is decoupled from UI, `MenuBarManager`
handles the status item, views are pure SwiftUI. Adding a second feature panel requires
no refactoring, just new files alongside existing ones.

Building a separate app means a second menubar icon, separate build pipeline, and
duplicated plumbing. Expanding zentempo means one app, one icon, one popover — timer
and skills side by side.

## Design

### Navigation: Tab-based popover

The current popover (`MenuBarView`) becomes one tab in a two-tab layout:

```
┌─────────────────────────────────┐
│  [Timer]  [Skills]              │  ← Segmented picker at top
├─────────────────────────────────┤
│                                 │
│  (current tab content)          │
│                                 │
└─────────────────────────────────┘
```

- **Timer tab** — existing `MenuBarView` content, unchanged
- **Skills tab** — new `TelosView` with agent/skill browser and launcher

The popover width stays at 300pt. Height grows slightly to ~450pt to accommodate
the tab picker without cramping the timer view.

### Skills tab layout

```
┌─────────────────────────────────┐
│  [Timer]  [Skills]              │
├─────────────────────────────────┤
│                                 │
│  ┌─ Agents ──────────────────┐  │
│  │ ▸ arxiv          3 skills │  │
│  │ ▸ hackernews     1 skill  │  │
│  │ ▸ kairos         7 skills │  │
│  │ ▸ clickup        1 skill  │  │
│  │ ▸ apple-calendar 1 skill  │  │
│  └───────────────────────────┘  │
│                                 │
│  ┌─ Quick Run ───────────────┐  │
│  │ ░░░░░░░░░░░░░░░░░░░░░░░░ │  │  ← Text field
│  │           [Run]           │  │
│  └───────────────────────────┘  │
│                                 │
│  Settings              Quit     │
└─────────────────────────────────┘
```

**Agent list**: Disclosure groups. Tap an agent to expand and see its skills.
Each skill row shows name + description. Tapping a skill populates the quick run
field with a suggested command.

**Quick run**: Text field + Run button. Types natural language, executes
`telos --agent <agent> "<input>"` via `Process`. The agent is auto-selected from
the expanded agent, or inferred by telos routing if none is selected.

### Expanded skill view

Tapping a skill row expands inline or navigates to a detail view:

```
┌─────────────────────────────────┐
│  ← Back to agents               │
├─────────────────────────────────┤
│  arxiv / trending               │
│                                 │
│  Fetch trending papers from     │
│  an arXiv category              │
│                                 │
│  ┌─────────────────────────┐    │
│  │ trending in cs.CL       │    │
│  │              [Run]       │    │
│  └─────────────────────────┘    │
│                                 │
│  Last run: 2026-02-22           │
│  Output: ~/obsidian/telos/arxiv/2026-... │
│                                 │
└─────────────────────────────────┘
```

### Execution & output

When the user hits Run:

1. Button shows a spinner / "Running..." state
2. `Process` executes: `uv run --project ~/workspace/telos telos --agent <agent> "<input>"`
3. Stdout/stderr captured via `Pipe`
4. On completion:
   - Success: show "Done" with link to output file (click opens in default app)
   - Failure: show error inline in red
5. State resets after 5 seconds

Output files are not displayed in the popover — they open in Obsidian or Finder.
The menubar app is a launcher, not a viewer.

## New Files

All new files go in `zentempo/zentempo/` alongside existing code.

### `TelosManager.swift` — data layer

```
TelosManager: ObservableObject
  @Published var agents: [TelosAgent]
  @Published var isRunning: Bool
  @Published var lastResult: RunResult?

  func refresh()              // calls `telos agents` + `telos list-skills --agent X` for each
  func run(agent:, input:)    // calls `telos --agent <agent> "<input>"` via Process

TelosAgent
  name: String
  skillCount: Int
  skills: [TelosSkill]

TelosSkill
  name: String
  description: String

RunResult
  success: Bool
  output: String
  outputFile: String?         // parsed from telos output if present
```

**Shell execution pattern:**

```swift
func shell(_ command: String) -> (output: String, exitCode: Int32) {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/bin/zsh")
    process.arguments = ["-lc", command]
    let pipe = Pipe()
    process.standardOutput = pipe
    process.standardError = pipe
    try? process.run()
    process.waitUntilExit()
    let data = pipe.fileHandleForReading.readDataToEndOfFile()
    let output = String(data: data, encoding: .utf8) ?? ""
    return (output, process.terminationStatus)
}
```

Use `-lc` (login shell) so the `uv` PATH and any aliases are available.

**Refresh strategy**: Call `refresh()` once on app launch and when the Skills tab
is selected. Cache results in memory — agent/skill lists don't change mid-session.
Add a manual refresh button for when the user installs new packs.

### `TelosView.swift` — skills tab UI

```
TelosView: View
  @ObservedObject var telosManager: TelosManager
  @State var selectedAgent: TelosAgent?
  @State var runInput: String
  @State var isExpanded: [String: Bool]     // agent name → expanded

  - List of agents as DisclosureGroups
  - Each skill row: name, description, tap to populate runInput
  - Text field + Run button at bottom
  - Inline status for run results
```

### `MainPopoverView.swift` — tab container

```
MainPopoverView: View
  @State var selectedTab: Tab = .timer
  enum Tab { case timer, skills }

  - Picker("", selection: $selectedTab) with .segmented style
  - Switch on selectedTab to show MenuBarView or TelosView
```

This replaces `MenuBarView` as the popover's root view. `MenuBarView` itself
is untouched — it just becomes the content of the timer tab.

## Changes to Existing Files

### `MenuBarManager.swift`

- Change `NSHostingController(rootView: MenuBarView(timer: timer))` to
  `NSHostingController(rootView: MainPopoverView(timer: timer, telosManager: telosManager))`
- Accept `telosManager` in init alongside `timer`
- Increase popover height: `contentSize = NSSize(width: 300, height: 450)`

### `zentempoApp.swift` (AppDelegate)

- Add `var telosManager = TelosManager()` alongside existing `var timer`
- Pass both to `MenuBarManager(timer: timer, telosManager: telosManager)`
- Call `telosManager.refresh()` in `applicationDidFinishLaunching`

### `zentempo.entitlements`

- Current: read-only file access in sandbox
- Needed: ability to spawn `Process` (shell out to telos)
- If sandboxed: may need to disable sandbox or add `com.apple.security.temporary-exception.mach-lookup`
- Simplest path: **disable app sandbox** since this is a personal tool, not App Store.
  Set `com.apple.security.app-sandbox` to `false`.

## Files NOT changed

- `PomodoroTimer.swift` — untouched
- `MenuBarView.swift` — untouched (becomes timer tab content)
- `SettingsView.swift` — untouched (opened from timer tab as before)
- `ContentView.swift` — still unused, can be deleted separately

## Implementation Order

1. **`TelosManager.swift`** — build and test the data layer first. Verify `Process`
   calls work, parse `telos agents` and `telos list-skills` output correctly.
2. **`TelosView.swift`** — build the skills UI against mock data, then wire to
   TelosManager.
3. **`MainPopoverView.swift`** — create the tab container, embed both views.
4. **Update `MenuBarManager.swift`** — swap root view to MainPopoverView.
5. **Update `zentempoApp.swift`** — instantiate TelosManager, pass to MenuBarManager.
6. **Update entitlements** — disable sandbox for Process spawning.
7. **Test end-to-end** — install, browse agents, run a skill, verify output.

## Edge Cases

- **telos not installed**: `refresh()` fails gracefully, shows "telos not found —
  install with `uv pip install -e ~/workspace/telos`" in the skills tab.
- **Long-running skill**: Run button shows spinner, disable input. Add a Cancel
  button that calls `process.terminate()`.
- **No agents installed**: Show empty state with "No agents installed" message.
- **Process PATH**: Use `/bin/zsh -lc` to inherit login shell PATH (where `uv` lives).
  This avoids hardcoding paths.

## Future Extensions (not in v1)

- **Favorites / pinned skills** — star frequently used skills for quick access
- **Run history** — last 10 runs with timestamps and output file links
- **Scheduled skills** — wire to existing timer infrastructure for recurring runs
- **Output preview** — render markdown output inline instead of opening externally
- **Keyboard shortcut** — global hotkey to open the skills tab directly
- **Skill search** — filter/search across all agents when the list gets long

## Testing

```bash
# Build from command line
xcodebuild -project zentempo/zentempo.xcodeproj -scheme zentempo build

# Run existing tests (should still pass — no changes to PomodoroTimer)
xcodebuild -project zentempo/zentempo.xcodeproj -scheme zentempo test

# Manual testing
# 1. Launch app, verify timer tab works as before
# 2. Switch to skills tab, verify agents load
# 3. Expand an agent, verify skills listed
# 4. Tap a skill, verify quick run populates
# 5. Run a skill (e.g. "trending"), verify spinner → done → output file link
# 6. Click output file link, verify it opens
```

New unit tests for `TelosManager`:
- Test `shell()` helper returns output and exit code
- Test agent list parsing from `telos agents` output
- Test skill list parsing from `telos list-skills` output
- Test `run()` with mock Process
- Test error handling when telos is not installed
