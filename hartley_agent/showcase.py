"""Cinematic Showcase and Animation Tour for Hartley (Zero Emojis).

Demonstrates all themes, boot sequences, dynamic thinking visualizers,
tool execution spinners, card layouts, safety badges, and palettes in full motion.
"""

import os
import sys
import time
from typing import List, Optional

from .animations import (
    ThinkingVisualizer,
    ToolExecutionVisualizer,
    animate_card_reveal,
    is_active,
    play_boot_sequence,
)
from .config import get_config_val, is_animations_enabled, set_config_val
from .themes import (
    BOLD,
    DIM,
    RESET,
    THEMES,
    Theme,
    get_theme,
    list_themes,
)

# Sample terminal commands tailored to each theme's personality
THEME_SCENARIOS = {
    "modern": {
        "query": "Find all TypeScript files excluding node_modules",
        "command": "find . -name '*.ts' -not -path '*/node_modules/*'",
        "output": "./src/agent.ts\n./src/client.ts\n./src/index.ts",
        "sample_cmd": "git status --short",
    },
    "hacker": {
        "query": "Probe local subnet for open SSH and HTTPS sockets",
        "command": "nmap -sS -T4 -p 22,443 192.168.1.0/24",
        "output": "PORT 22/tcp  OPEN  OpenSSH 9.6\nPORT 443/tcp OPEN  nginx 1.24",
        "sample_cmd": "netstat -tuln | grep LISTEN",
    },
    "steampunk": {
        "query": "Calibrate boiler pressure valves and engage clockwork governor",
        "command": "boiler-ctl --regulate-pressure --boiler 2 --target 140psi",
        "output": "[VALVE-A] RELEASE ENGAGED: 138 PSI\n[GEAR-04] GOVERNOR BALANCED AT 240 RPM",
        "sample_cmd": "gauge-read --all-tubes",
    },
    "cyberpunk": {
        "query": "Inject ICE breaker daemon into Arisaka subnet terminal",
        "command": "ice-drill --protocol neural-mesh --target arisaka-subnet",
        "output": "// ICE BREAKER INJECTED\n// SUBNET ACCESS: ELEVATED TO ADMIN",
        "sample_cmd": "cyberdeck --status --mesh",
    },
    "synthwave": {
        "query": "Align vector horizon scanlines to 128 BPM synthesizer grid",
        "command": "vector-synth --tempo 128bpm --grid outrun-sunset",
        "output": "~ ~ ~ BPM SYNC LOCK: 128.000 ~ ~ ~\n~ ~ ~ VECTOR CRT GRID: ALIGNED ~ ~ ~",
        "sample_cmd": "grid-scan --render-wireframe",
    },
    "mono": {
        "query": "Inspect git commit graph with compact decorated oneline format",
        "command": "git log --graph --oneline --decorate -n 3",
        "output": "* 8f2a1b9 (HEAD -> main) feat: add cinematic animations\n* c3d4e5f feat: add terminal themes\n* 1a2b3c4 init: gemini agent core",
        "sample_cmd": "git status -sb",
    },
}


def typewriter_print(text: str, delay: float = 0.015, color: str = "") -> None:
    """Print text with typewriter character-by-character animation."""
    if not (is_animations_enabled() and sys.stdout.isatty()):
        print(f"{color}{text}{RESET}")
        return

    sys.stdout.write(color)
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write(f"{RESET}\n")
    sys.stdout.flush()


def preview_spinner(theme: Theme, duration: float = 0.8) -> None:
    """Animate a short preview of the theme's spinner frames."""
    if not (is_animations_enabled() and sys.stdout.isatty()):
        frames_str = " ".join(theme.spinner_frames)
        print(f"  {theme.muted}Spinner Frames:{RESET} {theme.accent}{frames_str}{RESET}")
        return

    sys.stdout.write("\033[?25l")
    sys.stdout.flush()
    start = time.time()
    idx = 0
    frames = theme.spinner_frames

    try:
        while time.time() - start < duration:
            frame = frames[idx % len(frames)]
            sys.stdout.write(
                f"\r  {theme.muted}Live Spinner Cycle:{RESET} "
                f"{theme.primary}{frame}{RESET} "
                f"{theme.accent}[ {idx % len(frames) + 1}/{len(frames)} ]{RESET} "
                f"{theme.muted}({theme.display_name}){RESET}"
            )
            sys.stdout.flush()
            idx += 1
            time.sleep(0.09)
    finally:
        sys.stdout.write("\r\033[K\033[?25h")
        sys.stdout.flush()

    frames_str = " ".join(frames)
    print(f"  {theme.muted}Spinner Sequence:{RESET} {theme.primary}{frames_str}{RESET}")


def render_palette_swatches(theme: Theme) -> str:
    """Generate color swatch breakdown for a theme."""
    p = theme.primary
    a = theme.accent
    s = theme.secondary
    suc = theme.success
    w = theme.warning
    d = theme.danger
    m = theme.muted
    t = theme.text

    swatches = [
        f"{p}■ Primary{RESET}",
        f"{a}■ Accent{RESET}",
        f"{s}■ Secondary{RESET}",
        f"{suc}■ Success{RESET}",
        f"{w}■ Warning{RESET}",
        f"{d}■ Danger{RESET}",
        f"{m}■ Muted{RESET}",
        f"{t}■ Text{RESET}",
    ]
    return "  " + "   ".join(swatches[:4]) + "\n  " + "   ".join(swatches[4:])


def render_box_anatomy(theme: Theme) -> str:
    """Render the box drawing anatomy used by the theme."""
    tl, tr = theme.box_tl, theme.box_tr
    bl, br = theme.box_bl, theme.box_br
    h, v = theme.box_h, theme.box_v

    sample = (
        f"{theme.primary}{tl}{h*18}{tr}{RESET}\n"
        f"  {theme.primary}{v}{RESET} {theme.accent}BORDERS: {tl} {tr} {bl} {br} {h} {v}{RESET} {theme.primary}{v}{RESET}\n"
        f"  {theme.primary}{bl}{h*18}{br}{RESET}"
    )
    return sample


def showcase_single_theme(
    theme_name_or_obj,
    interactive: bool = False,
    speed: float = 1.0,
    force_animations: bool = True,
) -> None:
    """
    Run a full, cinematic in-motion demonstration of a single theme.
    Shows the boot sequence, banner, typing, thinking visualizer,
    tool execution, safety cards, and color palette.
    """
    th: Theme = theme_name_or_obj if isinstance(theme_name_or_obj, Theme) else get_theme(theme_name_or_obj)
    scenario = THEME_SCENARIOS.get(
        th.name,
        {
            "query": "Search directory for log files older than 7 days",
            "command": "find . -name '*.log' -mtime +7",
            "output": "./logs/app.log.1\n./logs/debug.log.2",
            "sample_cmd": "uptime",
        },
    )

    is_tty = sys.stdout.isatty()
    active_theme = get_config_val("theme", "modern")
    active_mark = f" {BOLD}{th.success}[ACTIVE]{RESET}" if th.name == active_theme else ""

    sep = f"{th.primary}{th.box_h * 64}{RESET}"

    # 1. Theme Header Card
    print(f"\n{sep}")
    print(f"{th.primary}# THEME SHOWCASE:{RESET} {BOLD}{th.accent}{th.display_name.upper()}{RESET} [{th.name}]{active_mark}")
    print(f"{th.muted}Description:{RESET} {th.text}{th.description}{RESET}")
    print(f"{sep}\n")

    # 2. Color Palette & Box Anatomy
    print(f"{BOLD}{th.accent}[1/6] Palette & Typography Breakdown:{RESET}")
    print(render_palette_swatches(th))
    print(f"\n{BOLD}{th.accent}[2/6] Spinner & Border Anatomy:{RESET}")
    preview_spinner(th, duration=0.8 * speed if is_tty else 0.0)
    print(f"  {render_box_anatomy(th)}\n")

    if is_tty:
        time.sleep(0.3 * speed)

    # 3. Live Boot Sequence
    print(f"{BOLD}{th.accent}[3/6] Live Boot Sequence & Startup Banner:{RESET}")
    # Force playback of boot sequence for showcase
    if is_tty and force_animations:
        # Temporarily call internal theme booters directly to ensure live animation
        from .animations import (
            _boot_cyberpunk,
            _boot_hacker,
            _boot_modern,
            _boot_mono,
            _boot_steampunk,
            _boot_synthwave,
        )
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()
        try:
            bname = th.name.lower()
            if bname == "hacker":
                _boot_hacker(th)
            elif bname == "cyberpunk":
                _boot_cyberpunk(th)
            elif bname == "steampunk":
                _boot_steampunk(th)
            elif bname == "synthwave":
                _boot_synthwave(th)
            elif bname == "mono":
                _boot_mono(th)
            else:
                _boot_modern(th)
        except Exception:
            pass
        finally:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()

    print(th.render_banner())
    print()

    if is_tty:
        time.sleep(0.4 * speed)

    # 4. Simulated User Input with Typewriter Effect
    print(f"{BOLD}{th.accent}[4/6] Prompt & Query Interaction:{RESET}")
    sys.stdout.write(f"{th.primary}{th.prompt_symbol}{RESET}")
    sys.stdout.flush()
    typewriter_print(scenario["query"], delay=0.018 * speed, color=th.text)

    # 5. Live Thinking Visualizer
    print(f"\n{BOLD}{th.accent}[5/6] Dynamic Thinking Visualizer (Equalizer Waves + Live Stopwatch):{RESET}")
    if is_tty and force_animations:
        with ThinkingVisualizer(initial_text="Analyzing query intent", theme=th):
            time.sleep(1.4 * speed)
    else:
        print(f"  {th.primary}{th.spinner_frames[0]} {th.accent}[ ▂▃▅▆▇▆▅▃ ] {th.text}Analyzing query intent {th.muted}[ 1.4s]{RESET}")

    # 6. Formatted Command Card Reveal
    cmd_card = th.render_card(
        scenario["command"],
        risk_level="SAFE",
        risk_reason="Read-only query operation",
    )
    animate_card_reveal(cmd_card, theme=th)

    # 7. Live Tool Execution Visualizer & Output
    print(f"\n{BOLD}{th.accent}[6/6] Subprocess Execution Visualizer & Badges:{RESET}")
    if is_tty and force_animations:
        with ToolExecutionVisualizer(command=scenario["command"], theme=th):
            time.sleep(0.5 * speed)
    else:
        print(f"  {th.primary}$ {scenario['command']}{RESET}")

    # Output lines
    for line in scenario["output"].splitlines():
        print(f"  {th.muted}{line}{RESET}")
    print(f"  {th.success}[+] Exit 0 (0.02s){RESET}\n")

    # 8. Multi-Risk Safety Badges
    print(f"{BOLD}{th.muted}Safety Assessment Levels in {th.display_name}:{RESET}")
    print(f"  SAFE:      {th.success}[OK] SAFE (Read-Only){RESET}")
    print(f"  MODERATE:  {th.warning}[!] MODERATE (File modification / network request){RESET}")
    print(f"  DANGEROUS: \033[41m\033[97m [!] DANGEROUS {RESET} {th.danger}Root or filesystem deletion blocked{RESET}\n")


def showcase_all_themes(
    interactive: bool = True,
    speed: float = 1.0,
    force_animations: bool = True,
) -> None:
    """
    Run an interactive or automated grand tour through all 8 Hartley themes.
    """
    themes = list_themes()
    total = len(themes)

    # Banner header
    print(f"\n\033[1m\033[96m╔══════════════════════════════════════════════════════════════╗\033[0m")
    print(f"\033[1m\033[96m║     [::] HARTLEY CINEMATIC THEME & ANIMATION SHOWCASE        ║\033[0m")
    print(f"\033[1m\033[96m║   6 Themed Environments // Boot Sequences // Visualizers    ║\033[0m")
    print(f"\033[1m\033[96m╚══════════════════════════════════════════════════════════════╝\033[0m\n")

    is_tty = sys.stdout.isatty() and sys.stdin.isatty() and interactive

    for idx, th in enumerate(themes, 1):
        print(f"\n\033[1;90m─── [ TOUR STEP {idx} of {total} ] ───────────────────────────────\033[0m")
        showcase_single_theme(th, interactive=False, speed=speed, force_animations=force_animations)

        if idx < total and is_tty:
            print(f"\033[1;96mActions for '{th.name}':\033[0m")
            print(f"  [Enter] Next theme  │  [s] Set as active  │  [q] Quit showcase")
            try:
                choice = input("\nChoice: ").strip().lower()
                if choice in ("q", "quit", "exit"):
                    print("\n\033[90mShowcase cancelled.\033[0m\n")
                    return
                elif choice in ("s", "set", "apply"):
                    set_config_val("theme", th.name)
                    print(f"{th.success}[OK] Theme set to {th.display_name}!{RESET}\n")
            except (KeyboardInterrupt, EOFError):
                print("\n\033[90mShowcase ended.\033[0m\n")
                return

    # Final summary gallery table
    print("\n\033[1m\033[96m╔══════════════════════════════════════════════════════════════╗\033[0m")
    print(f"\033[1m\033[96m║                 [+] SHOWCASE COMPLETED                       ║\033[0m")
    print(f"\033[1m\033[96m╚══════════════════════════════════════════════════════════════╝\033[0m\n")

    cur_theme = get_config_val("theme", "modern")
    print("\033[1mAvailable Themes Summary:\033[0m")
    for th in themes:
        mark = f" \033[1;92m(ACTIVE)\033[0m" if th.name == cur_theme else ""
        print(f"  {th.primary}●\033[0m \033[1m{th.display_name:<22}\033[0m \033[96mhartley theme set {th.name:<10}\033[0m{mark}")

    print(f"\n\033[90mTo switch themes anytime, run:\033[0m \033[1;96mhartley theme set <name>\033[0m")
    print(f"\033[90mTo preview a single theme again:\033[0m \033[1;96mhartley showcase <name>\033[0m\n")


def run_showcase(args: List[str]) -> int:
    """Entry point for `hartley showcase` or `hartley demo` command."""
    if not args:
        # Grand tour of all themes
        showcase_all_themes(interactive=True)
        return 0

    target = args[0].lower().strip()

    if target in ("all", "--all", "-a"):
        showcase_all_themes(interactive=True)
        return 0

    if target in ("fast", "--fast"):
        showcase_all_themes(interactive=False, speed=0.5)
        return 0

    if target in THEMES:
        showcase_single_theme(target, interactive=False)
        return 0

    avail = ", ".join(THEMES.keys())
    print(f"\033[91mUnknown theme '{target}'. Available themes: {avail}, all\033[0m")
    print(f"\033[90mUsage: hartley showcase [theme_name | all | --fast]\033[0m")
    return 1
