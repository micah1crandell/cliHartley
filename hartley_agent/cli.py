"""Command Line Interface entrypoint and command router for Hartley."""

import argparse
import sys
from typing import List, Optional

from . import __version__
from .agent import TerminalAgent
from .config import (
    ensure_api_key,
    get_api_key,
    get_api_key_source_description,
    get_config_file,
    get_config_val,
    is_animations_enabled,
    load_config,
    save_config,
    set_config_val,
)
from .gemini import GeminiClient
from .memory import GlobalMemory, WindowMemory
from .repl import run_repl
from .themes import THEMES, get_theme, list_themes, render_theme_gallery
from .ui import (
    BOLD,
    CYAN,
    DIM,
    GREEN,
    MAGENTA,
    RED,
    RESET,
    UNDERLINE,
    YELLOW,
    print_banner,
)


def print_help():
    """Print comprehensive Hartley help manual."""
    print_banner()
    print(f"""
{BOLD}Usage:{RESET}
  hartley                     Launch interactive AI terminal agent
  hartley c <query>           Generate a shell command with window memory
  hartley "<query>"           Shorthand command generation / conversation
  hartley run <goal>          Run autonomous multi-step task with tools
  hartley anim [on|off]       Toggle cinematic animations vs simple mode
  hartley loop                Launch 30-second cinematic fire & matrix loop animation
  hartley showcase [name|all] Live cinematic tour of all themes & animations
  hartley theme [set <name>]  Browse theme gallery or switch visual theme
  hartley key [api-key]       View status or set your Gemini API key
  hartley remember <fact>     Save instruction or preference to global memory
  hartley memory [show|clear] Inspect or manage global and window memory
  hartley clear               Reset conversation memory for this terminal window
  hartley e <command>         Explain a specific shell command
  hartley e results           Diagnose and explain previous command output / error
  hartley fix                 Diagnose last error from shell history/clipboard and fix it
  hartley config [cmd]        View or update configuration (model, API key, options)
  hartley --help              Show this help message
  hartley --version           Show version information

{BOLD}Examples:{RESET}
  {CYAN}hartley "what are my docker containers?"{RESET}
  {CYAN}hartley "stop the second one"{RESET}  (remembers prior window context!)
  {CYAN}hartley remember "always use pnpm instead of npm"{RESET}
  {CYAN}hartley run "clean up docker unused networks and images"{RESET}
  {CYAN}hartley memory{RESET}
  {CYAN}hartley clear{RESET}

{BOLD}Memory System:{RESET}
  • {BOLD}Window Memory:{RESET} Automatically tracks conversation and commands specific to
    this terminal tab/window.
  • {BOLD}Global Memory:{RESET} Persistent facts and preferences shared across ALL windows.
    Saved in ~/.config/hartley/global_memory.json.

{BOLD}Configuration & Free Tier:{RESET}
  Hartley uses Google's {BOLD}gemini-2.5-flash{RESET} by default (with automatic fallback
  to {BOLD}gemini-2.0-flash{RESET}). These models feature generous Google AI Studio Free Tier
  limits (up to 15 RPM, 1M TPM).
  Get your free API key at: {UNDERLINE}https://aistudio.google.com/app/apikey{RESET}
""")


def handle_config_cmd(args: List[str]) -> None:
    """Handle `hartley config` subcommands."""
    if not args or args[0] in ("show", "list"):
        config = load_config()
        print(f"\n{BOLD}{CYAN}Hartley Configuration:{RESET}")
        for k, v in config.items():
            display_v = "********" if k == "api_key" and v else str(v)
            print(f"  {BOLD}{k:20}{RESET}: {display_v}")
        print()
        return

    sub = args[0].lower()
    if sub == "get" and len(args) > 1:
        key = args[1]
        val = get_config_val(key)
        display_v = "********" if key == "api_key" and val else str(val)
        print(f"{key}: {display_v}")
    elif sub == "set" and len(args) > 2:
        key = args[1]
        val = " ".join(args[2:])
        set_config_val(key, val)
        display_v = "********" if key == "api_key" else val
        print(f"{GREEN}[OK] Set {key} = {display_v}{RESET}")
    else:
        print(f"{YELLOW}Usage: hartley config [show | get <key> | set <key> <val>]{RESET}")


def handle_anim_cmd(args: List[str]) -> int:
    """Handle `hartley anim` subcommands."""
    if not args:
        cur = is_animations_enabled()
        state = f"{GREEN}ENABLED (Cinematic mode){RESET}" if cur else f"{YELLOW}DISABLED (Simple mode){RESET}"
        print(f"\nHartley Animations: {state}")
        print(f"Usage: hartley anim [on | off | toggle]\n")
        return 0

    sub = args[0].lower()
    if sub in ("startup", "boot"):
        if len(args) > 1:
            st = args[1].lower() in ("on", "true", "1", "enable")
            set_config_val("startup_animation", st)
            state = f"{GREEN}ENABLED (30s Fire & Cyber Loop on startup){RESET}" if st else f"{YELLOW}DISABLED{RESET}"
            print(f"{GREEN}[OK] Startup animation {state}.{RESET}")
            return 0
        else:
            cur = get_config_val("startup_animation", True)
            state = f"{GREEN}ENABLED (Plays on startup){RESET}" if cur else f"{YELLOW}DISABLED{RESET}"
            print(f"\nHartley Startup Animation: {state}")
            print(f"Usage: hartley anim startup [on | off]\n")
            return 0

    if sub in ("on", "true", "1", "enable"):
        set_config_val("animations", True)
        print(f"{GREEN}[OK] Animations enabled (Cinematic mode).{RESET}")
        return 0
    elif sub in ("off", "false", "0", "disable"):
        set_config_val("animations", False)
        print(f"{GREEN}[OK] Animations disabled (Simple mode).{RESET}")
        return 0
    elif sub == "toggle":
        cur = is_animations_enabled()
        set_config_val("animations", not cur)
        state = "enabled (Cinematic mode)" if not cur else "disabled (Simple mode)"
        print(f"{GREEN}[OK] Animations {state}.{RESET}")
        return 0
    else:
        print(f"{YELLOW}Usage: hartley anim [on | off | toggle | startup on/off]{RESET}")
        return 1


def handle_showcase_cmd(args: List[str]) -> int:
    """Handle `hartley showcase` or `hartley demo` command."""
    from .showcase import run_showcase
    return run_showcase(args)


def handle_theme_cmd(args: List[str]) -> int:
    """Handle `hartley theme` subcommands."""
    if not args or args[0] in ("list", "gallery", "show"):
        print(render_theme_gallery())
        return 0

    sub = args[0].lower()
    if sub in ("showcase", "demo", "tour", "preview"):
        return handle_showcase_cmd(args[1:])

    target_theme = None
    if sub == "set" and len(args) > 1:
        target_theme = args[1].lower()
    elif sub in THEMES:
        target_theme = sub

    if target_theme:
        if target_theme in THEMES:
            set_config_val("theme", target_theme)
            th = THEMES[target_theme]
            print(f"{th.success}[OK] Switched theme to {BOLD}{th.display_name}{RESET} ({target_theme}){RESET}")
            print(f"{th.muted}Prompt preview: {th.primary}{th.prompt_symbol}{RESET}")
            return 0
        else:
            avail = ", ".join(THEMES.keys())
            print(f"{RED}Unknown theme '{target_theme}'. Available: {avail}{RESET}")
            return 1
    else:
        print(f"{YELLOW}Usage: hartley theme [list | showcase | set <name> | <name>]{RESET}")
        print(f"Available themes: {', '.join(THEMES.keys())}")
        return 1


def handle_key_cmd(args: List[str]) -> int:
    """Handle `hartley key` or `hartley auth` subcommands."""
    import os
    if args:
        new_key = args[0].strip().strip("\"'").strip()
        if not new_key:
            print(f"{RED}Error: API key cannot be empty.{RESET}")
            return 1
        set_config_val("api_key", new_key)
        cfg_file = get_config_file()
        masked = new_key[:6] + "..." + new_key[-4:] if len(new_key) > 10 else "***"
        print(f"{GREEN}[OK] Gemini API key saved successfully!{RESET}")
        print(f"  Saved to: {cfg_file}")
        print(f"  Key:      {masked} ({len(new_key)} chars)")
        if os.environ.get("GEMINI_API_KEY"):
            print(f"\n{YELLOW}Note: The environment variable $GEMINI_API_KEY is currently set in your shell.\nIf that environment variable has an invalid key, unset it with:\n  unset GEMINI_API_KEY{RESET}")
        return 0

    # Interactive key prompt / check
    source_desc = get_api_key_source_description()
    print(f"\n{BOLD}{CYAN}Hartley API Key Status:{RESET}")
    print(f"  Active Key Source: {source_desc}")
    print(f"  Config File:       {get_config_file()}")
    if os.environ.get("GEMINI_API_KEY"):
        print(f"\n{YELLOW}Note: The environment variable $GEMINI_API_KEY is currently set in your shell.{RESET}")

    try:
        new_key = input("\nEnter new Gemini API key (or press Enter to keep current): ").strip().strip("\"'").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        return 0

    if new_key:
        set_config_val("api_key", new_key)
        masked = new_key[:6] + "..." + new_key[-4:] if len(new_key) > 10 else "***"
        print(f"{GREEN}[OK] Saved API key ({masked}) to {get_config_file()}{RESET}\n")
    else:
        print("Kept existing key.\n")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entrypoint."""
    if argv is None:
        argv = sys.argv[1:]

    # Handle global flags first
    if not argv:
        # Launch REPL
        api_key = ensure_api_key()
        model = get_config_val("model", "gemini-2.5-flash")
        fallback_model = get_config_val("fallback_model", "gemini-2.0-flash")
        temp = get_config_val("temperature", 0.2)
        auto_safe = get_config_val("auto_approve_safe", True)

        client = GeminiClient(api_key=api_key, model=model, fallback_model=fallback_model, temperature=temp)
        agent = TerminalAgent(client=client, auto_approve_safe=auto_safe)
        run_repl(agent, client)
        return 0

    first = argv[0]

    if first in ("-h", "--help", "help", "h"):
        print_help()
        return 0

    if first in ("-v", "--version", "version"):
        model = get_config_val("model", "gemini-2.5-flash")
        print(f"Hartley v{__version__} (Gemini Model: {model})")
        return 0

    if first in ("anim", "animation", "animations"):
        return handle_anim_cmd(argv[1:])

    if first in ("showcase", "demo", "tour", "preview"):
        return handle_showcase_cmd(argv[1:])

    if first in ("loop", "fire", "cinema", "matrix"):
        import os
        import runpy
        script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fire_loop.py")
        if os.path.exists(script):
            runpy.run_path(script, run_name="__main__")
            return 0
        else:
            print("fire_loop.py not found.")
            return 1

    if first in ("key", "auth", "apikey"):
        return handle_key_cmd(argv[1:])

    if first == "config":
        handle_config_cmd(argv[1:])
        return 0

    if first in ("theme", "themes"):
        return handle_theme_cmd(argv[1:])

    if first in ("clear", "reset"):
        wm = WindowMemory()
        wm.clear()
        print(f"{GREEN}[OK] Cleared conversation memory for terminal window {wm.session_id}.{RESET}")
        return 0

    if first == "remember":
        gm = GlobalMemory()
        fact = " ".join(argv[1:]).strip()
        if not fact:
            print(f"{YELLOW}Usage: hartley remember <information to save globally>{RESET}")
            return 1
        entry = gm.add(fact)
        print(f"{GREEN}[OK] Saved to global memory [#{entry['id']}]:{RESET} {fact}")
        return 0

    if first == "memory":
        gm = GlobalMemory()
        wm = WindowMemory()
        sub = argv[1].lower() if len(argv) > 1 else "show"
        if sub == "clear":
            gm.clear()
            print(f"{GREEN}[OK] Cleared all global memory.{RESET}")
        elif sub in ("forget", "delete", "rm") and len(argv) > 2:
            try:
                eid = int(argv[2])
                if gm.remove(eid):
                    print(f"{GREEN}[OK] Removed item #{eid} from global memory.{RESET}")
                else:
                    print(f"{RED}Item #{eid} not found.{RESET}")
            except ValueError:
                print(f"{YELLOW}Usage: hartley memory forget <id>{RESET}")
        else:
            items = gm.load()
            print(f"\n{BOLD}{CYAN}Terminal Window Memory:{RESET}")
            print(f"  Window Session: {wm.session_id}")
            print(f"  Stored Turns:   {len(wm.load_messages())//2}")
            print(f"\n{BOLD}{CYAN}Global Memory (Persistent Across All Terminals):{RESET}")
            if not items:
                print(f"  {DIM}(No global memory items yet. Use 'hartley remember <fact>' to add){RESET}")
            else:
                for itm in items:
                    print(f"  {CYAN}#{itm['id']}{RESET} [{itm['timestamp']}] {itm['content']}")
            print()
        return 0

    # All other commands require Gemini API Key
    api_key = ensure_api_key()
    model = get_config_val("model", "gemini-2.5-flash")
    fallback_model = get_config_val("fallback_model", "gemini-2.0-flash")
    temp = get_config_val("temperature", 0.2)
    auto_safe = get_config_val("auto_approve_safe", True)

    client = GeminiClient(api_key=api_key, model=model, fallback_model=fallback_model, temperature=temp)
    agent = TerminalAgent(client=client, auto_approve_safe=auto_safe)

    if first == "c":
        # Generate command
        query = " ".join(argv[1:]).strip()
        if not query:
            print(f"{RED}Error: 'c' requires a query.{RESET}\nExample: hartley c 'list open ports'")
            return 1
        agent.generate_single_command(query)
        return 0

    if first == "run":
        # Multi-step autonomous agent goal
        goal = " ".join(argv[1:]).strip()
        if not goal:
            print(f"{RED}Error: 'run' requires a goal description.{RESET}")
            return 1
        agent.run_goal(goal)
        return 0

    if first == "e":
        # Explain command or results
        if len(argv) < 2:
            print(f"{RED}Error: 'e' command requires an argument.{RESET}\nExample: hartley e 'grep -rn pattern .'")
            return 1
        if argv[1] == "results":
            agent.explain_results()
        else:
            target_cmd = " ".join(argv[1:])
            agent.explain(target_cmd)
        return 0

    if first == "fix":
        # Diagnose and fix last command / error
        agent.explain_results()
        return 0

    # Default fallback: Treat arguments as command generation / conversational query
    query = " ".join(argv).strip()
    agent.generate_single_command(query)
    return 0


if __name__ == "__main__":
    sys.exit(main())
