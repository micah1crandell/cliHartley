# HARTLEY 2.0

> **Modern, Free-Tier-Optimized AI Terminal Agent for macOS powered by Google Gemini.**

Hartley transforms your command line into an intelligent pair programmer. It can generate optimal one-liners, explain complex shell incantations, diagnose errors from your terminal or clipboard, and autonomously execute multi-step tasks using native tool calling—all while staying strictly within the Google AI Studio **Free Tier**.

---

## Features

- **Powered by Gemini 2.5 Flash & 2.0 Flash**: High-speed reasoning and tool calling with zero API subscription cost.
- **Google AI Studio Free Tier Optimized**:
  - Automatic exponential backoff and retry on HTTP 429 (`RESOURCE_EXHAUSTED`).
  - Token-conscious prompt architecture and rolling context pruning.
  - Automatic fallback between `gemini-2.5-flash` and `gemini-2.0-flash`.
- **Cinematic Animations & Simple Mode**:
  - Themed startup boot sequences (RobCo memory counts, Matrix descrambler, pressure gauges, vector grids).
  - High-movement dynamic brain visualizer with audio equalizer waves and live stopwatch timing.
  - One-switch toggle between **Cinematic** (animated) and **Simple** (instant text) modes.
- **Autonomous ReAct Agent Loop (`hartley run`)**:
  - Full execution authority in your terminal: plans tasks, executes commands directly, reads files, inspects stdout/stderr, and dynamically recovers from failures without stopping on every step.
  - No 10-step limit: runs complex multi-step workflows to completion.
- **Fast One-Shot Generation (`hartley c` or `hartley "<query>"`)**:
  - Direct natural language command generation with instant Enter to run.
  - Automatically appends executed commands to your shell history (`~/.zsh_history`) so Up Arrow works immediately.
- **Diagnostics & Error Fixing (`hartley fix` / `hartley e results`)**:
  - Reads your last terminal command and clipboard error output to diagnose why a command failed and suggest immediate fixes.
- **Hardcoded Danger Guardrails**:
  - Seamless full authority for all routine operations (Docker, Git, builds, filesystem inspection, network tools).
  - Explicit confirmation prompts exclusively for genuinely destructive commands (`rm`, `sudo`, `dd`, `diskutil erase*`, `chmod -R 777`, `git reset --hard`).
- **8 Visual UI Themes**:
  - Transform your terminal with custom palettes, ASCII/Unicode box-drawing art, banners, prompt glyphs, and spinner animations.
  - Themes include: Modern Glass, Fallout Pip-Boy, Hacker Matrix, Steampunk Clockwork, Old School DOS, Cyberpunk Neon, Synthwave Outrun, and Monochrome Minimal.
- **Zero External Dependencies & Zero Emojis**:
  - Pure Python 3 standard library. Instant startup (<50ms), no pip compile steps, clean typographic technical aesthetics.

---

## Quickstart

### 1. Installation

Clone or navigate to the repository and run the installer:

```bash
chmod +x installHartley.sh
./installHartley.sh
```

This creates an executable symlink in `~/.local/bin/hartley`. Ensure `~/.local/bin` is in your `$PATH`:

```bash
# Add to ~/.zshrc or ~/.bashrc if needed:
export PATH="$HOME/.local/bin:$PATH"
```

### 2. Set Your Free Gemini API Key

Hartley requires a Google Gemini API key. Free keys can be created in seconds:

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey) and generate a free API key.
2. Set it using either:

```bash
# Option A: Hartley Key Command (Recommended - persists across restarts)
hartley key "your_api_key_here"

# Option B: Environment Variable (add to ~/.zshrc)
export GEMINI_API_KEY="your_api_key_here"
```

> **Note:** Hartley natively supports both Google's modern `AQ.` Authentication Keys and legacy `AIza` standard keys via the official `x-goog-api-key` header.

---

## Usage Guide

### 1. Interactive Agent REPL

Launch the interactive chat interface by running `hartley` without arguments:

```bash
hartley
```

Inside the REPL:
- Type any question or terminal task.
- Use `/run <goal>` to launch an autonomous multi-step agent.
- Use `/anim [on|off|toggle]` to switch between cinematic animations and simple mode.
- Use `/theme <name>` to view or switch UI themes dynamically.
- Use `/remember <fact>` to save global memory across all terminals.
- Use `/memory` to view current window and global memory.
- Use `/clear` to clear the terminal and reset conversation context.
- Use `/model` to view the active Gemini model.
- Use `/exit` or `Ctrl+D` to quit.

### 2. One-Shot Command Generation

Ask Hartley for a command directly from your shell:

```bash
hartley c "find all video files larger than 500MB and sort by size"
# or shorthand:
hartley "kill whatever process is listening on port 8080"
```

Hartley generates the optimal macOS command and presents:
```text
[::] Suggested Command:
       $ lsof -ti:8080 | xargs kill -9
     [!] MODERATE Modifies processes or executes programs
Execute now? [Y/n/e/c]:
```

### 3. Autonomous Multi-Step Tasks

Let Hartley plan and execute a complete workflow:

```bash
hartley run "create a python virtual environment, install pytest, and run the test suite"
```

Hartley will inspect the repository, run each step, inspect the outputs, recover from any errors, and confirm success.

### 4. Terminal Window & Global Memory

Hartley maintains two layers of memory:

1. **Window-Specific Memory (Automatic)**:
   - Each terminal tab/window has its own private conversational memory.
   - You can have a continuous multi-step dialogue in your shell across separate `hartley` commands:
   ```bash
   hartley "what docker containers are running?"
   # then in the same terminal window:
   hartley "stop the second one"
   # Hartley remembers which container was the second one from earlier in this window!
   ```
   - Clear window memory anytime:
   ```bash
   hartley clear
   ```

2. **Global Memory (Cross-Window)**:
   - Save persistent preferences, instructions, or infrastructure facts shared across **all** terminal windows:
   ```bash
   # Save a global fact or rule:
   hartley remember "always use pnpm instead of npm"
   hartley remember "docker mac host gateway is 192.168.65.2"

   # Inspect all memory:
   hartley memory

   # Delete or clear global memory:
   hartley memory forget 1
   hartley memory clear
   ```
   - Hartley automatically injects your global facts into the agent prompt across all windows!

### 5. Movement, Animations & Simple Mode

Hartley features rich visual motion and movement that communicates active thought and system execution:

- **Audio-Frequency Wave Equalizer**: Oscillating frequency bars (`[ ▂▃▅▆▇▆▅▃ ]`) with live stopwatch execution time.
- **Brain Activity Phases**: Cycling status notifications (`Analyzing intent` -> `Inspecting shell context` -> `Synthesizing command pipeline`).
- **Themed Startup Sequences**: Custom boot sequences for all 8 themes.

```bash
# Check animation status:
hartley anim

# Enable cinematic animations:
hartley anim on

# Switch to simple mode (instant output, zero delays):
hartley anim off

# Toggle between modes:
hartley anim toggle
```

### 6. Visual Themes System

Hartley includes 6 distinct visual themes that alter color palettes, ANSI styling, box-drawing characters, banner artwork, prompt symbols, and spinner frames:

| Theme Key | Name | Aesthetic & Style | Prompt Symbol |
|:---|:---|:---|:---|
| `modern` | **Modern Glass** *(Default)* | Refined macOS developer styling with electric cyan accents | `hartley >> ` |
| `hacker` | **Hacker Matrix** | Cyberspace deck with high-contrast Matrix lime green phosphor | `root@hartley:# ` |
| `steampunk` | **Steampunk Clockwork** | Victorian burnished brass, copper tubing, pressure gauges, and cogs | `[STEAM] HARTLEY >> ` |
| `cyberpunk` | **Cyberpunk Neon** | Night City neon pink and turquoise electric synth aesthetics | `CYBER//DECK>> ` |
| `synthwave` | **Synthwave Outrun** | 1984 arcade sunset violet, radiant coral, and VHS gridlines | `OUTRUN ~> ` |
| `mono` | **Monochrome Minimal** | Distraction-free typographic minimalism with pure white and charcoal | `h: ` |

```bash
# Preview the visual theme gallery:
hartley theme

# Switch your theme from shell:
hartley theme set cyberpunk
hartley theme hacker

# Or switch inside the interactive REPL:
/theme steampunk
```

### 7. Cinematic Animation & Theme Showcase

Experience all 6 themes in full motion with live boot sequences, neural thinking wave equalizers, subprocess execution visualizers, prompt typing, and safety assessment cards:

```bash
# Live interactive tour of all 6 themes and animations:
hartley showcase

# Fast tour of all themes:
hartley showcase --fast

# In-depth showcase of a single theme:
hartley showcase steampunk
hartley showcase cyberpunk
hartley showcase hacker

# Inside the interactive REPL:
/showcase
/showcase hacker
```

---

## Configuration

View or update Hartley settings:

```bash
# Display current configuration
hartley config show

# Change default model
hartley config set model gemini-2.5-flash

# Toggle animations
hartley config set animations true

# Enable auto-approval for safe read-only commands
hartley config set auto_approve_safe true

# Adjust agent temperature (e.g. 0.1 for strict commands, 0.5 for creativity)
hartley config set temperature 0.2
```

Settings are stored in `~/.config/hartley/config.json`.

---

## Testing

Run the test suite:

```bash
python3 -m unittest discover tests -v
```

---

## License & Acknowledgments

Originally inspired by `cligpt`. Rebuilt for macOS, Gemini 2.5 Flash, and Google AI Studio Free Tier.
