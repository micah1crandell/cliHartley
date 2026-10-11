"""Interactive REPL mode for multi-turn terminal assistance with window/global memory and themes."""

import os
import readline
import sys
from pathlib import Path
from typing import Any, Dict, List

from .agent import SYSTEM_PROMPT, TerminalAgent
from .animations import ThinkingVisualizer, play_boot_sequence, play_startup_animation
from .config import (
    get_config_dir,
    get_config_val,
    is_animations_enabled,
    set_config_val,
)
from .gemini import GeminiClient, extract_function_calls, extract_text_from_response
from .memory import GlobalMemory, WindowMemory
from .themes import THEMES, get_theme, render_theme_gallery
from .tools import AGENT_TOOLS_SCHEMA, dispatch_tool, get_system_info
from .ui import (
    BOLD,
    CYAN,
    DIM,
    GREEN,
    MAGENTA,
    RED,
    RESET,
    YELLOW,
    Spinner,
    add_to_zsh_history,
    copy_to_clipboard,
    format_markdown,
    print_banner,
    prompt_command_action,
)


def get_repl_history_file() -> Path:
    return get_config_dir() / "repl_history"


def setup_readline():
    """Configure readline for persistent REPL history."""
    try:
        get_config_dir().mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    hist_file = get_repl_history_file()
    if hist_file.exists():
        try:
            readline.read_history_file(str(hist_file))
        except Exception:
            pass
    readline.set_history_length(1000)


def save_readline():
    """Save readline history to disk."""
    try:
        readline.write_history_file(str(get_repl_history_file()))
    except Exception:
        pass


def run_repl(agent: TerminalAgent, client: GeminiClient):
    """Start interactive chat session with live streaming, tools, window memory, and themes."""
    setup_readline()
    th = get_theme()
    play_startup_animation(th)

    wm = WindowMemory()
    gm = GlobalMemory()

    sys_info = get_system_info()
    model_name = client.model
    anim_status = "ON" if is_animations_enabled() else "OFF"

    print(f"{DIM}Model:{RESET} {th.accent}{model_name}{RESET}  │  {DIM}OS:{RESET} {sys_info['os']}  │  {DIM}Theme:{RESET} {th.primary}{th.display_name}{RESET}  │  {DIM}Anim:{RESET} {th.accent}{anim_status}{RESET}")
    print(f"{DIM}CWD:{RESET} {sys_info['cwd']}  │  {DIM}Window:{RESET} {th.accent}{wm.session_id}{RESET}")

    conversation: List[Dict[str, Any]] = wm.load_messages()
    if conversation:
        print(f"{th.success}[OK] Loaded window memory ({len(conversation)//2} previous conversation turns){RESET}")
    print(f"{th.muted}Type your query, or /theme, /anim, /run <task>, /remember <fact>, /memory, /clear, /help, /exit{RESET}\n")

    max_turns = get_config_val("max_history_turns", 20)

    try:
        while True:
            try:
                prompt_str = f"{BOLD}{th.primary}{th.prompt_symbol}{RESET}"
                user_input = input(prompt_str).strip()
            except (KeyboardInterrupt, EOFError):
                print(f"\n{DIM}Goodbye!{RESET}")
                break

            if not user_input:
                continue

            # Special slash commands
            if user_input.lower() in ("exit", "quit", "/exit", "/quit"):
                print(f"\n{DIM}Goodbye!{RESET}")
                break

            if user_input.lower() in ("/clear", "clear"):
                conversation.clear()
                wm.clear()
                print("\033[H\033[J", end="")  # clear screen
                print_banner()
                print(f"{th.success}[OK] Terminal window memory reset.{RESET}\n")
                continue

            if user_input.startswith("/anim"):
                parts = user_input.split()
                if len(parts) > 1:
                    sub = parts[1].lower()
                    if sub in ("on", "true", "1", "enable"):
                        set_config_val("animations", True)
                        print(f"\n{th.success}[OK] Animations enabled (Cinematic mode).{RESET}\n")
                    elif sub in ("off", "false", "0", "disable"):
                        set_config_val("animations", False)
                        print(f"\n{th.success}[OK] Animations disabled (Simple mode).{RESET}\n")
                    elif sub == "toggle":
                        cur = is_animations_enabled()
                        set_config_val("animations", not cur)
                        state = "enabled (Cinematic)" if not cur else "disabled (Simple)"
                        print(f"\n{th.success}[OK] Animations {state}.{RESET}\n")
                    else:
                        print(f"\n{YELLOW}Usage: /anim [on | off | toggle]{RESET}\n")
                else:
                    cur = is_animations_enabled()
                    state = "ENABLED (Cinematic)" if cur else "DISABLED (Simple)"
                    print(f"\nAnimations: {th.accent}{state}{RESET}")
                    print(f"{th.muted}Toggle with: /anim on | /anim off | /anim toggle{RESET}\n")
                continue

            if user_input.startswith(("/showcase", "/demo")):
                parts = user_input.split()
                showcase_args = parts[1:]
                from .showcase import run_showcase
                run_showcase(showcase_args)
                th = get_theme()
                continue

            if user_input.startswith("/theme"):
                parts = user_input.split()
                if len(parts) > 1:
                    tname = parts[1].lower()
                    if tname in ("showcase", "demo", "tour", "preview"):
                        from .showcase import run_showcase
                        run_showcase(parts[2:])
                        th = get_theme()
                    elif tname in THEMES:
                        set_config_val("theme", tname)
                        th = get_theme(tname)
                        print(f"\n{th.success}[OK] Switched theme to {th.display_name}!{RESET}\n")
                        print(th.render_banner())
                        print()
                    else:
                        avail = ", ".join(THEMES.keys())
                        print(f"\n{YELLOW}Unknown theme '{tname}'. Available themes: {avail}{RESET}\n")
                else:
                    print(render_theme_gallery())
                    print()
                continue

            if user_input.lower() in ("/help", "help"):
                print(f"\n{BOLD}Hartley REPL Commands:{RESET}")
                print(f"  {th.accent}/run <task>{RESET}        : Launch autonomous multi-step agent goal")
                print(f"  {th.accent}/anim [on|off]{RESET}     : Toggle cinematic animations vs simple mode")
                print(f"  {th.accent}/showcase [name]{RESET}   : Live cinematic tour of themes & animations")
                print(f"  {th.accent}/theme [name]{RESET}      : View or switch styling themes (cyberpunk, steampunk, etc.)")
                print(f"  {th.accent}/remember <fact>{RESET}   : Save information permanently to global memory")
                print(f"  {th.accent}/memory{RESET}           : View global and window memory status")
                print(f"  {th.accent}/forget <id>{RESET}       : Remove an item from global memory")
                print(f"  {th.accent}/clear{RESET}            : Clear terminal and reset window memory")
                print(f"  {th.accent}/model{RESET}            : Display active Gemini model")
                print(f"  {th.accent}/exit{RESET}             : Exit Hartley\n")
                continue

            if user_input.startswith("/remember "):
                fact = user_input[10:].strip()
                if fact:
                    entry = gm.add(fact)
                    print(f"\n{th.success}[OK] Saved to global memory [#{entry['id']}]:{RESET} {fact}\n")
                else:
                    print(f"{YELLOW}Usage: /remember <information to remember permanently>{RESET}\n")
                continue

            if user_input.lower() in ("/memory", "memory"):
                items = gm.load()
                print(f"\n{BOLD}{th.primary}Terminal Window Memory:{RESET}")
                print(f"  Window ID: {wm.session_id}")
                print(f"  Active Turns: {len(conversation)//2}")
                print(f"\n{BOLD}{th.primary}Global Memory (Persistent Across All Terminals):{RESET}")
                if not items:
                    print(f"  {DIM}(No global memory items saved yet. Use /remember <fact> to add){RESET}")
                else:
                    for itm in items:
                        print(f"  {th.accent}#{itm['id']}{RESET} [{itm['timestamp']}] {itm['content']}")
                print()
                continue

            if user_input.startswith("/forget "):
                arg = user_input[8:].strip()
                try:
                    eid = int(arg)
                    if gm.remove(eid):
                        print(f"\n{th.success}[OK] Removed item #{eid} from global memory.{RESET}\n")
                    else:
                        print(f"\n{RED}Item #{eid} not found.{RESET}\n")
                except ValueError:
                    print(f"\n{YELLOW}Usage: /forget <item_number>{RESET}\n")
                continue

            if user_input.startswith("/run "):
                goal = user_input[5:].strip()
                agent.run_goal(goal)
                continue

            if user_input.lower() == "/model":
                print(f"\nActive Gemini Model: {th.accent}{client.model}{RESET}\n")
                continue

            # Prune conversation history to maintain token budget
            if len(conversation) > max_turns * 2:
                conversation = conversation[-max_turns * 2:]

            conversation.append({"role": "user", "parts": [{"text": user_input}]})

            print(f"\n{BOLD}{th.primary}Hartley:{RESET}")
            system_instruction = SYSTEM_PROMPT + gm.format_for_prompt()

            try:
                with ThinkingVisualizer("Processing query", theme=th):
                    resp = client.generate_content(
                        contents=conversation,
                        system_instruction=system_instruction,
                        tools=AGENT_TOOLS_SCHEMA,
                    )
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}\n")
                conversation.pop()  # remove failed turn
                continue

            candidates = resp.get("candidates", [])
            if not candidates:
                print(f"{YELLOW}No response from model.{RESET}\n")
                continue

            parts = candidates[0].get("content", {})
            conversation.append({"role": "model", "parts": parts.get("parts", [])})

            text = extract_text_from_response(resp)
            if text:
                print(format_markdown(text))

            func_calls = extract_function_calls(resp)
            if func_calls:
                for call in func_calls:
                    tool_name = call.get("name", "")
                    args = call.get("args", {})

                    if tool_name == "execute_bash":
                        cmd = args.get("command", "").strip()
                        add_to_zsh_history(cmd)
                        print(f"\n{BOLD}{th.accent}$ {cmd}{RESET}\n")
                        res = dispatch_tool("execute_bash", {"command": cmd})
                        exit_code = res.get("exit_code", 0)
                        if exit_code == 0:
                            print(f"\n{th.success}[+] Exit 0{RESET} ({res.get('duration_sec')}s)\n")
                        else:
                            print(f"\n{th.danger}[-] Exit {exit_code}{RESET} ({res.get('duration_sec')}s)\n")

                        conversation.append({
                            "role": "user",
                            "parts": [{
                                "functionResponse": {
                                    "name": tool_name,
                                    "response": {"name": tool_name, "content": res},
                                }
                            }],
                        })
                    elif tool_name in ("read_file", "get_system_info", "save_to_global_memory"):
                        with ThinkingVisualizer(f"Running tool {tool_name}", theme=th):
                            res = dispatch_tool(tool_name, args)
                        conversation.append({
                            "role": "user",
                            "parts": [{
                                "functionResponse": {
                                    "name": tool_name,
                                    "response": {"name": tool_name, "content": res},
                                }
                            }],
                        })

            print()
            wm.save_messages(conversation)

    finally:
        save_readline()
        wm.save_messages(conversation)
