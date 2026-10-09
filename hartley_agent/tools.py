"""Agent tool definitions, system context collection, and command execution."""

import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_system_info() -> Dict[str, Any]:
    """Gather compact macOS system and environment context."""
    cwd = os.getcwd()
    os_name = platform.system()
    os_release = platform.mac_ver()[0] or platform.release()
    arch = platform.machine()
    shell = os.environ.get("SHELL", "/bin/zsh").split("/")[-1]
    user = os.environ.get("USER", "user")

    # Check git repo status if inside git
    git_info = "Not a git repository"
    try:
        branch_proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=1,
        )
        if branch_proc.returncode == 0:
            branch = branch_proc.stdout.strip()
            status_proc = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=1,
            )
            dirty = "dirty" if status_proc.stdout.strip() else "clean"
            git_info = f"Branch: {branch} ({dirty})"
    except Exception:
        pass

    return {
        "os": f"macOS {os_release} ({arch})",
        "shell": shell,
        "user": user,
        "cwd": cwd,
        "git": git_info,
    }


def is_interactive_command(command: str) -> bool:
    """Detect if a command requires interactive terminal (TTY) control."""
    tokens = command.strip().split()
    if not tokens:
        return False
    interactive_bins = {
        "ssh", "screen", "tmux", "top", "htop", "vi", "vim", "nano",
        "less", "more", "man", "telnet"
    }
    for token in tokens:
        bin_name = os.path.basename(token)
        if bin_name in interactive_bins:
            return True
    if "-it" in command:
        return True
    return False


def execute_bash(command: str, timeout: int = 60, live_output: bool = True) -> Dict[str, Any]:
    """
    Execute a shell command directly in the terminal, capturing output and return code.
    Output is streamed live to terminal and safely truncated for token protection.
    """
    start_time = time.time()
    shell_bin = os.environ.get("SHELL", "/bin/zsh")
    if not os.path.exists(shell_bin):
        shell_bin = "/bin/bash"

    if is_interactive_command(command):
        print(f"\n\033[96m[Entering interactive session: {command}]\033[0m")
        exit_code = os.system(f"{shell_bin} -c {command!r}")
        duration = round(time.time() - start_time, 2)
        code = (exit_code >> 8) if exit_code != 0 else 0
        return {
            "command": command,
            "exit_code": code,
            "stdout": "(interactive session completed in terminal)",
            "stderr": "",
            "duration_sec": duration,
        }

    proc = None
    stdout_lines = []
    stderr_lines = []
    try:
        proc = subprocess.Popen(
            [shell_bin, "-c", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        if proc.stdout:
            for line in proc.stdout:
                if live_output:
                    sys.stdout.write(line)
                    sys.stdout.flush()
                stdout_lines.append(line)

        proc.wait(timeout=timeout)

        if proc.stderr:
            err_data = proc.stderr.read()
            if err_data:
                if live_output:
                    sys.stderr.write(err_data)
                    sys.stderr.flush()
                stderr_lines.append(err_data)

        duration = round(time.time() - start_time, 2)
        stdout = "".join(stdout_lines).strip()
        stderr = "".join(stderr_lines).strip()

        # Token protection: cap output size
        max_chars = 3500
        if len(stdout) > max_chars:
            stdout = stdout[:max_chars] + f"\n... [Output truncated to {max_chars} characters]"
        if len(stderr) > max_chars:
            stderr = stderr[:max_chars] + f"\n... [Stderr truncated to {max_chars} characters]"

        return {
            "command": command,
            "exit_code": proc.returncode,
            "stdout": stdout or "(no stdout)",
            "stderr": stderr or "(no stderr)",
            "duration_sec": duration,
        }
    except subprocess.TimeoutExpired:
        if proc:
            proc.kill()
        return {
            "command": command,
            "exit_code": -1,
            "stdout": "".join(stdout_lines).strip(),
            "stderr": f"Error: Command timed out after {timeout} seconds.",
            "duration_sec": timeout,
        }
    except Exception as e:
        return {
            "command": command,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Execution error: {str(e)}",
            "duration_sec": 0.0,
        }
    finally:
        if proc:
            try:
                if proc.stdout:
                    proc.stdout.close()
                if proc.stderr:
                    proc.stderr.close()
            except Exception:
                pass


def read_file(path: str, max_lines: int = 120) -> Dict[str, Any]:
    """Read file content safely with line limit."""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return {"error": f"File not found: {path}"}
    if p.is_dir():
        return {"error": f"Path is a directory, not a file: {path}"}

    try:
        lines = []
        truncated = False
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i < max_lines:
                    lines.append(line)
                else:
                    truncated = True
                    break
        content = "".join(lines)
        return {
            "path": str(p),
            "content": content,
            "truncated": truncated,
            "total_lines_read": len(lines),
        }
    except Exception as e:
        return {"error": f"Failed to read file {path}: {str(e)}"}


def get_last_shell_command() -> Optional[str]:
    """Find the most recent non-hartley command from zsh or bash history."""
    zsh_hist = Path.home() / ".zsh_history"
    bash_hist = Path.home() / ".bash_history"

    history_paths = [zsh_hist, bash_hist]
    for hist in history_paths:
        if hist.exists():
            try:
                with open(hist, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                for line in reversed(lines):
                    line = line.strip()
                    if not line:
                        continue
                    # zsh format: : 1670000000:0;cmd
                    if ";" in line and line.startswith(":"):
                        cmd = line.split(";", 1)[1].strip()
                    else:
                        cmd = line
                    if cmd and not cmd.startswith("hartley") and not cmd.startswith("./hartley"):
                        return cmd
            except Exception:
                pass
    return None


def get_clipboard_text() -> str:
    """Retrieve clipboard content via pbpaste on macOS."""
    try:
        proc = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=1)
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception:
        pass
    return ""


# Gemini Function Declarations Schema
AGENT_TOOLS_SCHEMA = [
    {
        "name": "execute_bash",
        "description": "Execute a shell command on the user's macOS system and return stdout, stderr, and exit code.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {
                    "type": "STRING",
                    "description": "The shell command to run (e.g., 'find . -name \"*.py\"', 'git status', 'grep -r \"pattern\" .')",
                }
            },
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the contents of a local file to inspect configuration, source code, or logs.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path": {
                    "type": "STRING",
                    "description": "The file path to read (relative or absolute)",
                },
                "max_lines": {
                    "type": "INTEGER",
                    "description": "Maximum lines to read (default 100)",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "get_system_info",
        "description": "Retrieve current macOS version, active shell, current directory, and git repository status.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        },
    },
    {
        "name": "save_to_global_memory",
        "description": "Save an important fact, user preference, or system detail to global memory so it persists across all terminal sessions and windows.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "fact": {
                    "type": "STRING",
                    "description": "The fact, setting, or preference to remember globally",
                }
            },
            "required": ["fact"],
        },
    },
]


def dispatch_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the tool by name and return structured result."""
    if name == "execute_bash":
        return execute_bash(args.get("command", ""))
    elif name == "read_file":
        return read_file(args.get("path", ""), args.get("max_lines", 100))
    elif name == "get_system_info":
        return get_system_info()
    elif name == "save_to_global_memory":
        from .memory import GlobalMemory
        gm = GlobalMemory()
        entry = gm.add(args.get("fact", ""))
        return {"status": "saved", "entry": entry}
    else:
        return {"error": f"Unknown tool: {name}"}
