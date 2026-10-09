"""Configuration and environment management for Hartley."""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_CONFIG: Dict[str, Any] = {
    "model": "gemini-2.5-flash",
    "fallback_model": "gemini-2.0-flash",
    "temperature": 0.2,
    "auto_approve_safe": False,
    "max_history_turns": 15,
    "theme": "modern",
    "animations": True,
    "api_key": "",
}

_RESOLVED_CONFIG_DIR: Optional[Path] = None


def get_config_dir() -> Path:
    """Resolve a writable config directory, with fallback for sandbox/permission restrictions."""
    global _RESOLVED_CONFIG_DIR
    if _RESOLVED_CONFIG_DIR is not None:
        return _RESOLVED_CONFIG_DIR

    # 1. Custom env var
    env_dir = os.environ.get("HARTLEY_CONFIG_DIR")
    if env_dir:
        p = Path(env_dir).expanduser()
        try:
            p.mkdir(parents=True, exist_ok=True)
            _RESOLVED_CONFIG_DIR = p
            return p
        except Exception:
            pass

    # 2. Standard ~/.config/hartley
    std_dir = Path.home() / ".config" / "hartley"
    try:
        std_dir.mkdir(parents=True, exist_ok=True)
        # Test writability
        test_file = std_dir / ".write_test"
        with open(test_file, "w") as f:
            f.write("ok")
        test_file.unlink(missing_ok=True)
        _RESOLVED_CONFIG_DIR = std_dir
        return std_dir
    except (PermissionError, OSError):
        pass

    # 3. User home fallback directory ~/.hartley (persists across cd / restarts)
    home_dir = Path.home() / ".hartley"
    try:
        home_dir.mkdir(parents=True, exist_ok=True)
        test_file = home_dir / ".write_test"
        with open(test_file, "w") as f:
            f.write("ok")
        test_file.unlink(missing_ok=True)
        _RESOLVED_CONFIG_DIR = home_dir
        return home_dir
    except (PermissionError, OSError):
        pass

    # 4. Local workspace fallback directory
    local_dir = Path.cwd() / ".hartley"
    try:
        local_dir.mkdir(parents=True, exist_ok=True)
        _RESOLVED_CONFIG_DIR = local_dir
        return local_dir
    except Exception:
        pass

    # 5. Final fallback
    _RESOLVED_CONFIG_DIR = Path(".")
    return _RESOLVED_CONFIG_DIR


def get_config_file() -> Path:
    """Return path to config.json."""
    return get_config_dir() / "config.json"


def load_config() -> Dict[str, Any]:
    """Load configuration from disk, filling in defaults and checking candidate locations."""
    config = DEFAULT_CONFIG.copy()
    # Check fallback candidate locations first, primary get_config_file() last so it has highest precedence
    candidates = [
        Path.cwd() / ".hartley" / "config.json",
        Path.home() / ".hartley" / "config.json",
        Path.home() / ".config" / "hartley" / "config.json",
        get_config_file(),
    ]
    seen = set()
    for cfg_file in candidates:
        if cfg_file in seen:
            continue
        seen.add(cfg_file)
        if cfg_file.exists():
            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    if isinstance(saved, dict):
                        for k, v in saved.items():
                            if v is not None:
                                if k == "api_key":
                                    clean_k = str(v).strip().strip("\"'").strip()
                                    if clean_k:
                                        config[k] = clean_k
                                else:
                                    config[k] = v
            except Exception:
                pass
    return config


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to disk."""
    cfg_dir = get_config_dir()
    try:
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg_file = cfg_dir / "config.json"
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except (PermissionError, OSError) as e:
        sys.stderr.write(f"\033[93mWarning: Could not save config to {cfg_dir}: {e}\033[0m\n")


def get_config_val(key: str, default: Any = None) -> Any:
    """Get a configuration value."""
    config = load_config()
    return config.get(key, default if default is not None else DEFAULT_CONFIG.get(key))


def set_config_val(key: str, value: Any) -> None:
    """Set a single configuration value."""
    config = load_config()
    if key in ("auto_approve_safe",):
        if isinstance(value, str):
            value = value.strip().lower() in ("true", "1", "yes", "y")
    elif key in ("animations",):
        if isinstance(value, str):
            value = value.strip().lower() in ("true", "1", "yes", "y", "on", "enable")
        else:
            value = bool(value)
    elif key in ("max_history_turns",):
        value = int(value)
    elif key in ("temperature",):
        value = float(value)
    elif key in ("api_key",):
        if isinstance(value, str):
            value = value.strip().strip("\"'").strip()
    config[key] = value
    save_config(config)


def is_animations_enabled() -> bool:
    """Return whether terminal animations are enabled."""
    val = get_config_val("animations", True)
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes", "y", "on", "enable")
    return bool(val)


def get_api_key(explicit_key: Optional[str] = None) -> Optional[str]:
    """Resolve Gemini API key from explicit arg, env var, or config file."""
    if explicit_key and explicit_key.strip():
        return explicit_key.strip().strip("\"'").strip()

    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key.strip("\"'").strip()

    config = load_config()
    stored_key = config.get("api_key", "")
    if stored_key and isinstance(stored_key, str) and stored_key.strip():
        return stored_key.strip().strip("\"'").strip()

    return None


def get_api_key_source_description() -> str:
    """Return a human-readable description of where the active API key came from."""
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        clean = env_key.strip("\"'").strip()
        masked = clean[:6] + "..." + clean[-4:] if len(clean) > 10 else "***"
        return f"environment variable $GEMINI_API_KEY ({masked})"

    config = load_config()
    stored_key = config.get("api_key", "")
    if stored_key and isinstance(stored_key, str) and stored_key.strip():
        clean = stored_key.strip().strip("\"'").strip()
        masked = clean[:6] + "..." + clean[-4:] if len(clean) > 10 else "***"
        return f"config file {get_config_file()} ({masked})"

    return "none (no key configured)"


def ensure_api_key(explicit_key: Optional[str] = None, interactive: bool = True) -> str:
    """Ensure an API key is available, prompting the user if necessary."""
    key = get_api_key(explicit_key)
    if key:
        return key

    if not interactive or not sys.stdin.isatty():
        print(
            "\033[91mError: GEMINI_API_KEY is not set.\033[0m\n"
            "Please set your key using either:\n"
            "  1. export GEMINI_API_KEY=\"your_key_here\"\n"
            "  2. hartley config set api_key \"your_key_here\"\n"
            "Get a free Gemini API key at: https://aistudio.google.com/app/apikey",
            file=sys.stderr,
        )
        sys.exit(1)

    print("\033[1;36m┌──────────────────────────────────────────────────────────┐\033[0m")
    print("\033[1;36m│ Welcome to Hartley! A Gemini API key is required.        │\033[0m")
    print("\033[1;36m│ You can get a FREE key at:                               │\033[0m")
    print("\033[1;36m│ \033[4;34mhttps://aistudio.google.com/app/apikey\033[0m\033[1;36m                   │\033[0m")
    print("\033[1;36m└──────────────────────────────────────────────────────────┘\033[0m")

    try:
        user_input = input("\nEnter your Gemini API key: ").strip().strip("\"'").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nSetup cancelled.")
        sys.exit(1)

    if not user_input:
        print("\033[91mNo API key provided. Exiting.\033[0m", file=sys.stderr)
        sys.exit(1)

    set_config_val("api_key", user_input)
    print(f"\033[92m[OK] API key saved to {get_config_file()}\033[0m\n")
    return user_input
