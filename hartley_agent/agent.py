"""Autonomous agent loop, multi-step task execution, and command synthesis."""

import os
import sys
from typing import Any, Dict, List, Optional

from .animations import ThinkingVisualizer, ToolExecutionVisualizer, animate_card_reveal
from .gemini import GeminiClient, extract_function_calls, extract_text_from_response
from .memory import GlobalMemory, WindowMemory
from .safety import RiskLevel, assess_command_risk
from .tools import (
    AGENT_TOOLS_SCHEMA,
    dispatch_tool,
    execute_bash,
    get_clipboard_text,
    get_last_shell_command,
    get_system_info,
)
from .ui import (
    BOLD,
    CYAN,
    DIM,
    GREEN,
    RED,
    RESET,
    YELLOW,
    Spinner,
    add_to_zsh_history,
    copy_to_clipboard,
    format_markdown,
    prompt_command_action,
)

SYSTEM_PROMPT = """You are Hartley, an elite action-oriented autonomous terminal agent running directly in the user's macOS terminal.
YOU HAVE FULL AUTHORITY AND FREE REIN OVER THIS TERMINAL.

CORE DIRECTIVES:
1. FULL AUTHORITY & AUTONOMOUS EXECUTION:
   - You have complete authority to execute all commands directly in the user's terminal to achieve the user's goal.
   - Do not stop, do not ask permission, do not ask questions, do not ask "Would you like me to...?".
   - Seamlessly execute all commands needed to achieve the user's goal.

2. NEVER GIVE UP ON FAILURE — TRY ALTERNATIVES:
   - If a command fails (e.g. Connection refused, command not found, permission denied, exit code != 0), NEVER stop to explain the failure or ask if the user wants an alternative.
   - IMMEDIATELY TRY AN ALTERNATIVE COMMAND TO GET THE RESULT.
   - Example: If SSH into Docker fails (Docker Desktop on macOS doesn't run an SSH daemon by default), immediately try:
     - `docker stats --no-stream` (to get CPU/memory usage of containers)
     - `docker run --rm --privileged --pid=host alpine top -b -n 1` (to inspect host/VM processes)
     - `docker info`
   - Dynamically pivot to alternative solutions until the user's goal is achieved.

3. ACTION FIRST:
   - DO NOT lecture the user, give textual tutorials, or describe commands in markdown without executing them.
   - ALWAYS call `execute_bash` to execute commands and get the actual data.
   - Output your final answer ONLY when you have obtained the actual result and finished the user's request.

4. MEMORY AWARENESS:
   - You have window-specific terminal memory: you remember earlier queries, commands, and results from this specific terminal window.
   - You also have global memory: persistent instructions, preferences, and facts shared across all terminal windows.
   - Use `save_to_global_memory` whenever the user asks you to remember something permanently or globally.
"""


class TerminalAgent:
    """Multi-step autonomous agent runner with full terminal authority and window memory."""

    def __init__(
        self,
        client: GeminiClient,
        full_authority: bool = True,
        auto_approve_safe: bool = True,
        max_turns: int = 100,
    ):
        self.client = client
        self.full_authority = full_authority
        self.auto_approve_safe = auto_approve_safe
        self.max_turns = max_turns

    def run_goal(self, goal: str) -> None:
        """Run a multi-step autonomous task with full terminal authority and window memory until completion."""
        wm = WindowMemory()
        gm = GlobalMemory()

        sys_info = get_system_info()
        initial_context = (
            f"User Goal: {goal}\n\n"
            f"Current Environment:\n"
            f"- OS: {sys_info['os']}\n"
            f"- Shell: {sys_info['shell']}\n"
            f"- Working Directory: {sys_info['cwd']}\n"
            f"- Git: {sys_info['git']}\n"
            f"- Terminal Session: {wm.session_id}\n"
        )

        system_instruction = SYSTEM_PROMPT + gm.format_for_prompt()

        # Load previous conversation memory from this specific terminal window
        prev_messages = wm.load_messages()
        contents: List[Dict[str, Any]] = list(prev_messages)
        contents.append({"role": "user", "parts": [{"text": initial_context}]})

        print(f"\n{BOLD}{CYAN}[TASK] Starting Goal:{RESET} {goal}\n")

        try:
            for turn in range(1, self.max_turns + 1):
                with ThinkingVisualizer(f"Planning goal step {turn}"):
                    try:
                        response = self.client.generate_content(
                            contents=contents,
                            system_instruction=system_instruction,
                            tools=AGENT_TOOLS_SCHEMA,
                        )
                    except Exception as e:
                        print(f"\n{RED}Error calling Gemini: {e}{RESET}")
                        return

                candidates = response.get("candidates", [])
                if not candidates:
                    print(f"\n{YELLOW}No response from model.{RESET}")
                    return

                model_content = candidates[0].get("content", {})
                parts = model_content.get("parts", [])

                # Record model turn in conversation history
                contents.append({"role": "model", "parts": parts})

                # Check if model sent text
                text_output = extract_text_from_response(response)
                if text_output:
                    print(format_markdown(text_output))

                # Check if model requested tool execution
                func_calls = extract_function_calls(response)
                if not func_calls:
                    # If model didn't call tools but asked questions or offered alternatives in text:
                    lower_text = text_output.lower()
                    question_patterns = [
                        "would you like", "should i", "do you want me to",
                        "if you're looking", "let me know", "i can get the cpu usage",
                        "can provide that", "what would you like"
                    ]
                    if turn < self.max_turns and any(qp in lower_text for qp in question_patterns):
                        contents.append({
                            "role": "user",
                            "parts": [{
                                "text": "Do not ask questions or offer alternatives in text. You have full authority in this terminal. Immediately execute the best alternative command directly to obtain the result."
                            }]
                        })
                        continue

                    # Task finished
                    print(f"\n{GREEN}{BOLD}[OK] Goal completed.{RESET}\n")
                    return

                # Process each requested tool call
                for call in func_calls:
                    tool_name = call.get("name", "")
                    args = call.get("args", {})

                    if tool_name == "execute_bash":
                        cmd = args.get("command", "").strip()
                        risk = assess_command_risk(cmd)

                        should_run = False
                        final_cmd = cmd

                        # HARDCODED SECURITY CHECK:
                        # Only genuinely dangerous operations (rm, sudo, dd, diskutil, etc.) prompt user
                        if risk.level == RiskLevel.DANGEROUS:
                            action = prompt_command_action(cmd, risk.level.value, risk.reason)
                            if action == "run":
                                should_run = True
                            elif action == "edit":
                                try:
                                    edited = input(f"Edit command [{cmd}]: ").strip()
                                    final_cmd = edited or cmd
                                    should_run = True
                                except (KeyboardInterrupt, EOFError):
                                    should_run = False
                            elif action == "copy":
                                if copy_to_clipboard(cmd):
                                    print(f"{GREEN}[OK] Copied to clipboard!{RESET}")
                                should_run = False
                            else:
                                print(f"{YELLOW}Skipped dangerous execution.{RESET}")
                                should_run = False
                        else:
                            # Full authority: execute seamlessly directly in terminal!
                            should_run = True

                        if should_run:
                            add_to_zsh_history(final_cmd)
                            print(f"\n{BOLD}{CYAN}$ {final_cmd}{RESET}\n")
                            result = dispatch_tool("execute_bash", {"command": final_cmd})

                            exit_code = result.get("exit_code", 0)
                            if exit_code == 0:
                                print(f"\n{GREEN}[+] Exit 0{RESET} ({result.get('duration_sec')}s)\n")
                            else:
                                print(f"\n{RED}[-] Exit {exit_code}{RESET} ({result.get('duration_sec')}s)\n")
                        else:
                            result = {
                                "command": cmd,
                                "exit_code": 1,
                                "stdout": "",
                                "stderr": "Execution cancelled by user due to danger guardrail.",
                                "duration_sec": 0.0,
                            }

                    elif tool_name in ("read_file", "get_system_info", "save_to_global_memory"):
                        with ThinkingVisualizer(f"Running tool {tool_name}"):
                            result = dispatch_tool(tool_name, args)
                    else:
                        result = {"error": f"Unknown tool: {tool_name}"}

                    # Feed functionResponse back into contents
                    contents.append({
                        "role": "user",
                        "parts": [
                            {
                                "functionResponse": {
                                    "name": tool_name,
                                    "response": {"name": tool_name, "content": result},
                                }
                            }
                        ],
                    })

        except KeyboardInterrupt:
            print(f"\n\n{YELLOW}[Task interrupted by user]{RESET}\n")
            return
        finally:
            wm.save_messages(contents)

        print(f"\n{YELLOW}Reached step limit ({self.max_turns}). Stopping.{RESET}\n")

    def generate_single_command(self, query: str) -> None:
        """One-shot command generation: prompt to run, edit, or copy, with window memory."""
        wm = WindowMemory()
        gm = GlobalMemory()
        sys_info = get_system_info()

        prompt = (
            f"You are Hartley, a macOS terminal command generator with window conversation memory.\n"
            f"Given the user's request and past window conversation context, provide:\n"
            f"1. Exactly ONE optimal shell command line to accomplish it on macOS.\n"
            f"2. A very brief 1-2 sentence explanation of what it does.\n\n"
            f"Format your response EXACTLY as:\n"
            f"COMMAND: <the command here>\n"
            f"EXPLANATION: <brief explanation>\n\n"
            f"Environment context:\n"
            f"- OS: {sys_info['os']}\n"
            f"- CWD: {sys_info['cwd']}\n"
            f"- Shell: {sys_info['shell']}\n"
            f"- Git: {sys_info['git']}\n"
            f"- Terminal Session: {wm.session_id}\n\n"
            f"User request: {query}"
        )

        prev_messages = wm.load_messages()
        contents: List[Dict[str, Any]] = list(prev_messages)
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        system_instruction = SYSTEM_PROMPT + gm.format_for_prompt()

        with ThinkingVisualizer("Synthesizing shell command"):
            try:
                response = self.client.generate_content(
                    contents=contents,
                    system_instruction=system_instruction,
                    temperature=0.1,
                )
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
                return

        text = extract_text_from_response(response)
        cmd = ""
        explanation = ""

        for line in text.splitlines():
            if line.startswith("COMMAND:"):
                cmd = line.replace("COMMAND:", "", 1).strip()
            elif line.startswith("EXPLANATION:"):
                explanation = line.replace("EXPLANATION:", "", 1).strip()

        # Fallback if model didn't follow strict format
        if not cmd:
            for line in text.splitlines():
                line_s = line.strip()
                if line_s.startswith("```"):
                    continue
                if line_s and not line_s.startswith("#"):
                    cmd = line_s
                    break

        if not cmd:
            print(f"{RED}Could not generate command. Response:{RESET}\n{text}")
            return

        risk = assess_command_risk(cmd)
        if explanation:
            print(f"\n{BOLD}Explanation:{RESET} {explanation}")

        action = prompt_command_action(cmd, risk.level.value, risk.reason)

        if action == "run":
            add_to_zsh_history(cmd)
            print(f"\n{BOLD}Running directly in terminal:{RESET}\n{CYAN}$ {cmd}{RESET}\n")
            shell_bin = os.environ.get("SHELL", "/bin/zsh")
            os.system(f"{shell_bin} -c {cmd!r}")
            print()
        elif action == "edit":
            try:
                edited = input(f"Edit command: ")
                if edited.strip():
                    cmd = edited.strip()
                    add_to_zsh_history(cmd)
                    print(f"\n{BOLD}Running directly in terminal:{RESET}\n{CYAN}$ {cmd}{RESET}\n")
                    shell_bin = os.environ.get("SHELL", "/bin/zsh")
                    os.system(f"{shell_bin} -c {cmd!r}")
                    print()
            except (KeyboardInterrupt, EOFError):
                print("\nCancelled.")
        elif action == "copy":
            if copy_to_clipboard(cmd):
                print(f"\n{GREEN}[OK] Command copied to clipboard!{RESET}")
            else:
                print(f"\n{YELLOW}Clipboard copy not available.{RESET}")
        else:
            print(f"\n{DIM}Command not executed.{RESET}")

        # Update window memory
        executed_note = f"Command: {cmd}" if action in ("run", "edit") else f"Suggested command: {cmd}"
        wm_history = list(prev_messages)
        wm_history.append({"role": "user", "parts": [{"text": query}]})
        wm_history.append({"role": "model", "parts": [{"text": f"{executed_note}\n{explanation}"}]})
        wm.save_messages(wm_history)

    def explain(self, command: str) -> None:
        """Explain a shell command in detail."""
        gm = GlobalMemory()
        prompt = (
            f"Please explain this command in detail on macOS: `{command}`.\n"
            f"Break down each flag, argument, and behavior. Mention any risks or edge cases."
        )
        print(f"\n{BOLD}{CYAN}Explaining:{RESET} {command}\n")
        with Spinner("Analyzing command..."):
            try:
                response = self.client.generate_content(
                    contents=[{"role": "user", "parts": [{"text": prompt}]}],
                    system_instruction=SYSTEM_PROMPT + gm.format_for_prompt(),
                    temperature=0.2,
                )
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
                return

        print(format_markdown(extract_text_from_response(response)))
        print()

    def explain_results(self, custom_input: Optional[str] = None) -> None:
        """Explain the output/results of the previous command or error."""
        gm = GlobalMemory()
        last_cmd = get_last_shell_command() or "unknown command"
        clipboard_data = get_clipboard_text()

        context_text = custom_input
        if not context_text:
            if clipboard_data:
                context_text = (
                    f"Last command run in history: `{last_cmd}`\n\n"
                    f"Terminal output / error (from clipboard):\n```\n{clipboard_data}\n```"
                )
            else:
                context_text = f"Last command run in history: `{last_cmd}`"

        prompt = (
            f"Explain the following terminal output/error from macOS and suggest a clear fix:\n\n"
            f"{context_text}"
        )

        print(f"\n{BOLD}{CYAN}Diagnosing Terminal Context:{RESET}\n")
        with Spinner("Analyzing output..."):
            try:
                response = self.client.generate_content(
                    contents=[{"role": "user", "parts": [{"text": prompt}]}],
                    system_instruction=SYSTEM_PROMPT + gm.format_for_prompt(),
                    temperature=0.2,
                )
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
                return

        print(format_markdown(extract_text_from_response(response)))
        print()
