"""Terminal UI utilities: ANSI styling, spinners, boxes, and prompt helpers."""

import itertools
import os
import shutil
import subprocess
import sys
import threading
import time
from typing import Optional

from .themes import get_theme

# ANSI Escape Codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"
GRAY = "\033[90m"

BG_RED = "\033[41m"
BG_YELLOW = "\033[43m"
BG_BLUE = "\033[44m"


def term_width() -> int:
    """Return terminal width, defaulting to 80."""
    try:
        return shutil.get_terminal_size((80, 24)).columns
    except Exception:
        return 80


def print_banner() -> None:
    """Display the Hartley banner using active theme."""
    th = get_theme()
    print(th.render_banner())


def format_markdown(text: str) -> str:
    """Themed ANSI markdown formatter for terminal output."""
    th = get_theme()
    lines = text.split("\n")
    formatted = []
    in_code_block = False

    for line in lines:
        if line.startswith("```"):
            if in_code_block:
                in_code_block = False
                formatted.append(f"{th.muted}{th.box_bl}{th.box_h * 50}{RESET}")
            else:
                in_code_block = True
                lang = line.replace("```", "").strip()
                lang_tag = f" [{lang}]" if lang else ""
                formatted.append(f"{th.muted}{th.box_tl}{th.box_h * 2}{th.accent}{lang_tag}{th.muted}{th.box_h * 44}{RESET}")
            continue

        if in_code_block:
            formatted.append(f"  {th.text}{line}{RESET}")
            continue

        # Headers
        if line.startswith("### "):
            line = f"{BOLD}{th.primary}▸ {line[4:]}{RESET}"
        elif line.startswith("## "):
            line = f"{BOLD}{th.primary}▶ {line[3:]}{RESET}"
        elif line.startswith("# "):
            line = f"{BOLD}{UNDERLINE}{th.primary}{line[2:]}{RESET}"

        # Bullet points
        elif line.strip().startswith("- ") or line.strip().startswith("* "):
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            line = " " * indent + f"{th.accent}•{RESET} " + stripped[2:]

        # Inline code `foo`
        import re
        line = re.sub(r"`([^`]+)`", rf"{th.accent}\1{RESET}", line)
        # Bold **foo**
        line = re.sub(r"\*\*([^*]+)\*\*", rf"{BOLD}\1{RESET}", line)

        formatted.append(line)

    return "\n".join(formatted)


class Spinner:
    """Animated terminal spinner using active theme frames."""

    def __init__(self, message: str = "Thinking...", color: Optional[str] = None):
        th = get_theme()
        self.message = message
        self.color = color or th.primary
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._frames = th.spinner_frames

    def _spin(self):
        spinner_cycle = itertools.cycle(self._frames)
        while self.running:
            frame = next(spinner_cycle)
            sys.stdout.write(f"\r{self.color}{frame}{RESET} {self.message} ")
            sys.stdout.flush()
            time.sleep(0.09)
        # Clear line when done
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        if not sys.stdout.isatty():
            return
        self.running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self):
        if self.running:
            self.running = False
            if self._thread:
                self._thread.join(timeout=0.5)


def copy_to_clipboard(text: str) -> bool:
    """Copy text to macOS clipboard using pbcopy."""
    try:
        proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        proc.communicate(text.encode("utf-8"))
        return proc.returncode == 0
    except Exception:
        return False


def add_to_zsh_history(command: str) -> None:
    """Append command to zsh history so it's accessible via Up Arrow in shell."""
    zsh_history = os.path.expanduser("~/.zsh_history")
    try:
        timestamp = int(time.time())
        entry = f": {timestamp}:0;{command}\n"
        with open(zsh_history, "a", encoding="utf-8", errors="ignore") as f:
            f.write(entry)
    except Exception:
        pass


def prompt_command_action(command: str, risk_level: str = "MODERATE", risk_reason: str = "") -> str:
    """
    Render themed command card and prompt user for action.
    Returns: 'run', 'edit', 'copy', or 'skip'
    """
    th = get_theme()
    print(th.render_card(command, risk_level, risk_reason))

    if risk_level == "DANGEROUS":
        print(f"{th.danger}{BOLD}Caution: This command modifies critical files, disks, or system state!{RESET}")

    print(f"Action: {th.success}{BOLD}[y] Run directly (press Enter){RESET}  {th.warning}[e] Edit{RESET}  {th.accent}[c] Copy{RESET}  {th.danger}[n] Skip{RESET}")
    try:
        choice = input("Execute now? [Y/n/e/c]: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        return "skip"

    if not choice or choice in ("y", "yes"):
        return "run"
    elif choice in ("e", "edit"):
        return "edit"
    elif choice in ("c", "copy"):
        return "copy"
    else:
        return "skip"
