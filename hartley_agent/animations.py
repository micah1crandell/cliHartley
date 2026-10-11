"""Cinematic animation and experience engine for Hartley (Zero Emojis)."""

import os
import sys
import threading
import time
from typing import Any, Callable, Dict, Generator, List, Optional

from .config import is_animations_enabled
from .themes import Theme, get_theme


def is_active() -> bool:
    """Check if animations should actively render."""
    return is_animations_enabled() and sys.stdout.isatty()


# Wave / equalizer frames for thinking animations
WAVE_FRAMES: List[str] = [
    " ▂▃▅▆▇▆▅▃ ",
    "▂▃▅▆▇▆▅▃  ",
    "▃▅▆▇▆▅▃  ▂",
    "▅▆▇▆▅▃  ▂▃",
    "▆▇▆▅▃  ▂▃▅",
    "▇▆▅▃  ▂▃▅▆",
    "▆▅▃  ▂▃▅▆▇",
    "▅▃  ▂▃▅▆▇▆",
    "▃  ▂▃▅▆▇▆▅",
]

BRAILLE_WAVES: List[str] = [
    "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏",
    "⣾⣽⣻⢿⡿⣟⣯⣷",
    "⠁⠂⠄⡀⢀⠠⠐⠈",
]

THINKING_PHASES: List[str] = [
    "Analyzing query intent",
    "Inspecting shell environment [cwd, git, shell]",
    "Synthesizing terminal command pipeline",
    "Optimizing parameters for macOS",
    "Formulating reasoning and safety verification",
]


class ThinkingVisualizer:
    """
    High-movement dynamic thinking animation with wave equalizer,
    cycling brain phases, and live stopwatch timer.
    """

    def __init__(self, initial_text: str = "Processing", theme: Optional[Theme] = None):
        self.initial_text = initial_text
        self.theme = theme or get_theme()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._start_time = 0.0

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        self._start_time = time.time()
        if not is_active():
            # In simple mode, just print clean starting message
            sys.stdout.write(f"{self.theme.muted}[*] {self.initial_text}...{self.theme.text} ")
            sys.stdout.flush()
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()

    def _animate(self):
        th = self.theme
        frame_idx = 0
        phase_idx = 0
        last_phase_switch = time.time()
        current_phase = self.initial_text

        # Hide cursor
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

        try:
            while not self._stop_event.is_set():
                elapsed = time.time() - self._start_time

                # Cycle thinking phases every 1.4 seconds
                if time.time() - last_phase_switch > 1.4:
                    phase_idx = (phase_idx + 1) % len(THINKING_PHASES)
                    current_phase = THINKING_PHASES[phase_idx]
                    last_phase_switch = time.time()

                # Pick animation glyphs
                spinner_ch = th.spinner_frames[frame_idx % len(th.spinner_frames)]
                wave_str = WAVE_FRAMES[frame_idx % len(WAVE_FRAMES)]

                # Format animation line
                line = (
                    f"\r\033[K{th.primary}{spinner_ch} {th.accent}[{wave_str}] "
                    f"{th.text}{current_phase} "
                    f"{th.muted}[{elapsed:4.1f}s]\033[0m"
                )

                sys.stdout.write(line)
                sys.stdout.flush()

                frame_idx += 1
                time.sleep(0.065)
        finally:
            # Clear line and restore cursor
            sys.stdout.write("\r\033[K\033[?25h")
            sys.stdout.flush()

    def stop(self):
        if is_active():
            self._stop_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=0.3)
            sys.stdout.write("\r\033[K\033[?25h")
            sys.stdout.flush()
        else:
            sys.stdout.write("\n")
            sys.stdout.flush()


def play_startup_animation(theme: Optional[Theme] = None) -> None:
    """
    Play the 30-second thermal & cyber cinematic sequence on Hartley startup.
    Skipped if animations are disabled, non-interactive, or in automated tests.
    """
    th = theme or get_theme()
    if not is_active() or "unittest" in sys.modules or os.environ.get("HARTLEY_TESTING"):
        print(th.render_banner())
        return

    from .config import get_config_val
    if get_config_val("startup_animation", True):
        from .fire_engine import run_cinematic_animation
        run_cinematic_animation(is_interactive_boot=True)
        print(th.render_banner())
    else:
        play_boot_sequence(th)


def play_boot_sequence(theme: Optional[Theme] = None, skippable: bool = True) -> None:
    """
    Play a quick themed boot sequence on REPL startup (400-550ms).
    Skipped immediately if animations are disabled or non-interactive.
    """
    th = theme or get_theme()
    if not is_active():
        print(th.render_banner())
        return

    name = th.name.lower()

    # Hide cursor during sequence
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    try:
        if name == "hacker":
            _boot_hacker(th)
        elif name == "cyberpunk":
            _boot_cyberpunk(th)
        elif name == "steampunk":
            _boot_steampunk(th)
        elif name == "synthwave":
            _boot_synthwave(th)
        elif name == "mono":
            _boot_mono(th)
        else:
            _boot_modern(th)
    except (KeyboardInterrupt, Exception):
        pass
    finally:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

    print(th.render_banner())


def _boot_modern(th: Theme) -> None:
    steps = [
        ("INITIALIZING CORE", 0.15),
        ("CALIBRATING NEURAL MODELS", 0.45),
        ("CONNECTING GEMINI FLASH PROTOCOL", 0.80),
        ("SYSTEM ONLINE", 1.0),
    ]
    bar_width = 24
    for label, progress in steps:
        filled = int(bar_width * progress)
        empty = bar_width - filled
        bar = f"{th.primary}{'=' * filled}{th.accent}>{' ' * max(0, empty - 1)}"
        pct = int(progress * 100)
        sys.stdout.write(f"\r\033[K{th.muted}[SYSTEM] {th.text}[{bar}{th.text}] {th.accent}{pct:3d}% {th.muted}:: {label}\033[0m")
        sys.stdout.flush()
        time.sleep(0.08)
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()


def _boot_hacker(th: Theme) -> None:
    # Descrambler effect
    target = "ROOT ACCESS GRANTED // KERNEL HOOKS ACTIVE"
    charset = "01!@#$%^&*<>~+="
    import random

    for step in range(len(target) + 1):
        if step % 3 != 0 and step < len(target):
            continue
        revealed = target[:step]
        scrambled = "".join(random.choice(charset) for _ in range(min(12, len(target) - step)))
        sys.stdout.write(f"\r\033[K{th.primary}/* {th.accent}{revealed}{th.muted}{scrambled} {th.primary}*/\033[0m")
        sys.stdout.flush()
        time.sleep(0.02)
    time.sleep(0.08)
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()


def _boot_steampunk(th: Theme) -> None:
    pressures = [20, 55, 90, 120, 140]
    gear_glyphs = ["[/]", "[-]", "[\\]", "[|]"]
    for idx, psi in enumerate(pressures):
        gear = gear_glyphs[idx % len(gear_glyphs)]
        bar = "=" * (psi // 15)
        sys.stdout.write(f"\r\033[K{th.primary}{gear} STEAM PRESSURE: {th.accent}[{bar:<10}] {psi} PSI {th.muted}:: DIFFERENCE ENGINE SPINNING\033[0m")
        sys.stdout.flush()
        time.sleep(0.06)
    time.sleep(0.06)
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()


def _boot_cyberpunk(th: Theme) -> None:
    lines = [
        "// ICE BREAKER v2.0 // DEPLOYING NETRUNNER DAEMON",
        "CONNECTING TO SUBNET... [||||||||||||||||] 100%",
        "NEURAL LINK CALIBRATED // PROTOCOL 2077 ONLINE",
    ]
    for line in lines:
        sys.stdout.write(f"\r\033[K{th.primary}{line}\033[0m")
        sys.stdout.flush()
        time.sleep(0.09)
    time.sleep(0.06)
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()


def _boot_synthwave(th: Theme) -> None:
    grids = [
        "~ ~ ~ VECTOR HORIZON GRID SCAN [---] ~ ~ ~",
        "~ ~ ~ VECTOR HORIZON GRID SCAN [===] ~ ~ ~",
        "~ ~ ~ VHS TRACKING SYNC [OK] // OUTRUN ACTIVE ~ ~ ~",
    ]
    for g in grids:
        sys.stdout.write(f"\r\033[K{th.primary}{g}\033[0m")
        sys.stdout.flush()
        time.sleep(0.09)
    time.sleep(0.06)
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()


def _boot_mono(th: Theme) -> None:
    msg = "hartley terminal interface online."
    for idx in range(1, len(msg) + 1):
        sys.stdout.write(f"\r\033[Kh: {msg[:idx]}\033[7m \033[0m")
        sys.stdout.flush()
        time.sleep(0.012)
    time.sleep(0.06)
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()


def animate_card_reveal(card_text: str, theme: Optional[Theme] = None) -> None:
    """Reveal suggested command card smoothly line-by-line if animations are active."""
    th = theme or get_theme()
    if not is_active():
        print(card_text)
        return

    lines = card_text.splitlines()
    for line in lines:
        print(line)
        time.sleep(0.018)


class ToolExecutionVisualizer:
    """
    Live running timer and pulse badge for executing shell commands.
    """

    def __init__(self, command: str, theme: Optional[Theme] = None):
        self.command = command
        self.theme = theme or get_theme()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._start_time = 0.0

    def __enter__(self):
        self._start_time = time.time()
        th = self.theme
        if not is_active():
            print(f"\n{th.primary}$ {self.command}\033[0m\n")
            return self

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if is_active():
            self._stop_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=0.3)
            sys.stdout.write("\r\033[K\033[?25h")
            sys.stdout.flush()

    def _animate(self):
        th = self.theme
        frame_idx = 0
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

        try:
            while not self._stop_event.is_set():
                elapsed = time.time() - self._start_time
                spinner_ch = th.spinner_frames[frame_idx % len(th.spinner_frames)]
                truncated_cmd = self.command[:45] + "..." if len(self.command) > 48 else self.command
                line = (
                    f"\r\033[K{th.primary}{spinner_ch} {th.accent}[RUNNING] "
                    f"{th.text}$ {truncated_cmd} "
                    f"{th.muted}[{elapsed:4.1f}s]\033[0m"
                )
                sys.stdout.write(line)
                sys.stdout.flush()
                frame_idx += 1
                time.sleep(0.08)
        finally:
            sys.stdout.write("\r\033[K\033[?25h")
            sys.stdout.flush()
