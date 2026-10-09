"""Command safety classification and danger guardrails."""

import re
import shlex
from enum import Enum
from typing import List, NamedTuple


class RiskLevel(Enum):
    SAFE = "SAFE"
    MODERATE = "MODERATE"
    DANGEROUS = "DANGEROUS"


class SafetyReport(NamedTuple):
    level: RiskLevel
    reason: str
    command: str


SAFE_COMMANDS = {
    "cat", "head", "tail", "less", "more",
    "ls", "pwd", "tree", "file", "stat",
    "grep", "egrep", "fgrep", "rg", "ag",
    "find", "which", "whereis", "type",
    "echo", "printf", "printenv", "env",
    "uname", "whoami", "id", "groups", "date", "uptime",
    "ps", "top", "htop", "vm_stat",
    "df", "du",
    "wc", "sort", "uniq", "awk", "sed", "tr", "cut", "diff",
    "history", "fc", "man", "tldr",
    "sw_vers", "system_profiler",
}

SAFE_GIT_SUBCMDS = {
    "status", "log", "diff", "show", "branch", "tag", "remote", "rev-parse"
}

DANGEROUS_PATTERNS = [
    (r"\brm\s+-[a-zA-Z]*[rf][a-zA-Z]*\s+(/|~|\$HOME|\.\.|\*)", "High-risk recursive deletion targeting root, home, or wildcards"),
    (r"\brm\s+-[a-zA-Z]*[rf][a-zA-Z]*", "Recursive deletion of files/directories"),
    (r"\brm\s+", "File deletion command (rm)"),
    (r"\bsudo\b", "Command requires root/superuser privileges"),
    (r"\bdd\s+if=", "Low-level block write with dd"),
    (r"\bmkfs\b|\bfdisk\b", "Disk partitioning/formatting tool"),
    (r"\bdiskutil\s+(erase|partition|unmountDisk)", "Destructive macOS disk utility operation"),
    (r"\bchmod\s+-[a-zA-Z]*R[a-zA-Z]*\s+777", "Blanket permissive permission change (chmod -R 777)"),
    (r"\bgit\s+reset\s+--hard", "Destructive git reset --hard wipes all uncommitted work"),
    (r"\bgit\s+clean\s+-[a-zA-Z]*[fd][a-zA-Z]*", "Destructive git clean wipes untracked files"),
    (r"\bkill\s+-9\s+(-1|1\b)", "Attempting to kill system or all processes"),
    (r">\s*/dev/(disk|sd|nvme)", "Direct overwrite to raw block storage device"),
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", "Shell fork bomb pattern"),
    (r"\b(shutdown|reboot|halt|poweroff)\b", "System shutdown or reboot command"),
]


def assess_command_risk(command: str) -> SafetyReport:
    """Analyze a shell command and return its safety level and rationale."""
    cleaned = command.strip()
    if not cleaned:
        return SafetyReport(RiskLevel.SAFE, "Empty command", command)

    # 1. Check explicit dangerous patterns
    for pattern, reason in DANGEROUS_PATTERNS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            return SafetyReport(RiskLevel.DANGEROUS, reason, command)

    # 2. Check for output redirections that overwrite files (> or >>)
    has_output_redirection = bool(re.search(r"(?<![0-9])>{1,2}\s*[^\s&]", cleaned))

    # 3. Split command chain (e.g. pipes |, &&, ||, ;)
    segments = re.split(r"\s*(?:&&|\|\||;|\|)\s*", cleaned)
    all_segments_safe = True

    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        try:
            tokens = shlex.split(seg)
        except Exception:
            tokens = seg.split()

        if not tokens:
            continue

        cmd_name = tokens[0].split("/")[-1]

        if cmd_name == "git":
            if len(tokens) > 1 and tokens[1] in SAFE_GIT_SUBCMDS:
                continue
            all_segments_safe = False
            break
        elif cmd_name in SAFE_COMMANDS:
            continue
        else:
            all_segments_safe = False
            break

    if all_segments_safe and not has_output_redirection:
        return SafetyReport(RiskLevel.SAFE, "Read-only inspection command", command)

    return SafetyReport(RiskLevel.MODERATE, "Modifies files, git state, or executes external programs", command)
