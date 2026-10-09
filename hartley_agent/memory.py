"""Terminal window session memory and global memory management."""

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import get_config_dir


def get_terminal_window_id() -> str:
    """
    Compute a unique identifier for the current terminal window or tab on macOS.
    1. TERM_SESSION_ID (Apple Terminal and iTerm2 unique UUID per window/tab).
    2. TTY name (e.g. ttys002).
    3. POSIX Session ID (os.getsid).
    """
    # 1. Apple Terminal & iTerm2 session UUID
    term_session = os.environ.get("TERM_SESSION_ID")
    if term_session:
        # Sanitize for filename
        clean_id = re.sub(r"[^a-zA-Z0-9_-]", "_", term_session)
        return f"term_{clean_id}"

    # 2. Controlling TTY device name
    try:
        if sys.stdin.isatty():
            tty = os.ttyname(sys.stdin.fileno())
            clean_tty = re.sub(r"[^a-zA-Z0-9_-]", "_", os.path.basename(tty))
            return f"tty_{clean_tty}"
    except Exception:
        pass

    # 3. POSIX Session ID (unique per terminal shell process tree)
    try:
        sid = os.getsid(0)
        return f"session_{sid}"
    except Exception:
        pass

    # 4. Fallback: Parent process ID
    return f"ppid_{os.getppid()}"


class WindowMemory:
    """Manages conversational memory specific to a single terminal window/tab."""

    def __init__(self, session_id: Optional[str] = None, max_messages: int = 20):
        self.session_id = session_id or get_terminal_window_id()
        self.max_messages = max_messages
        self.sessions_dir = get_config_dir() / "sessions"

    def _get_session_file(self) -> Path:
        return self.sessions_dir / f"{self.session_id}.json"

    def load_messages(self) -> List[Dict[str, Any]]:
        """Load previous conversation turns for this terminal window."""
        session_file = self._get_session_file()
        if not session_file.exists():
            return []
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    msgs = data.get("messages", [])
                    if isinstance(msgs, list):
                        return msgs
        except Exception:
            pass
        return []

    def save_messages(self, messages: List[Dict[str, Any]]) -> None:
        """Save conversation turns for this terminal window, pruning to max_messages."""
        try:
            self.sessions_dir.mkdir(parents=True, exist_ok=True)
            # Prune to max_messages to protect Free Tier token allowance
            pruned = messages[-self.max_messages :] if len(messages) > self.max_messages else messages
            
            data = {
                "session_id": self.session_id,
                "updated_at": time.time(),
                "messages": pruned,
            }
            with open(self._get_session_file(), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            sys.stderr.write(f"\033[90m[Warning: Could not save window memory: {e}]\033[0m\n")

    def clear(self) -> None:
        """Clear memory for this specific terminal window."""
        session_file = self._get_session_file()
        if session_file.exists():
            try:
                session_file.unlink()
            except Exception:
                pass


class GlobalMemory:
    """Manages persistent memory and knowledge shared across ALL terminal windows."""

    def __init__(self):
        self.memory_file = get_config_dir() / "global_memory.json"

    def load(self) -> List[Dict[str, Any]]:
        """Load global memory items."""
        if not self.memory_file.exists():
            return []
        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "items" in data:
                    return data["items"]
        except Exception:
            pass
        return []

    def save(self, items: List[Dict[str, Any]]) -> None:
        """Save global memory items."""
        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump({"items": items, "updated_at": time.time()}, f, indent=2)
        except Exception as e:
            sys.stderr.write(f"\033[90m[Warning: Could not save global memory: {e}]\033[0m\n")

    def add(self, content: str) -> Dict[str, Any]:
        """Add a new memory fact or preference."""
        items = self.load()
        entry = {
            "id": len(items) + 1,
            "content": content.strip(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        items.append(entry)
        self.save(items)
        return entry

    def remove(self, entry_id: int) -> bool:
        """Remove a memory item by ID."""
        items = self.load()
        new_items = [item for item in items if item.get("id") != entry_id]
        if len(new_items) != len(items):
            # Reindex
            for i, itm in enumerate(new_items, 1):
                itm["id"] = i
            self.save(new_items)
            return True
        return False

    def clear(self) -> None:
        """Clear all global memory."""
        self.save([])

    def format_for_prompt(self) -> str:
        """Format global memory for system prompt injection."""
        items = self.load()
        if not items:
            return ""
        lines = ["\nUSER GLOBAL MEMORY (PERSISTENT FACTS ACROSS ALL TERMINAL WINDOWS):"]
        for itm in items:
            lines.append(f"- {itm['content']}")
        return "\n".join(lines) + "\n"
