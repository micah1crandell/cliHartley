"""Unit test suite for Hartley Terminal Agent."""

import json
import os
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from hartley_agent.agent import TerminalAgent
from hartley_agent.config import (
    get_api_key,
    get_config_val,
    load_config,
    set_config_val,
)
from hartley_agent.gemini import (
    GeminiAPIError,
    GeminiClient,
    extract_function_calls,
    extract_text_from_response,
)
from hartley_agent.safety import RiskLevel, assess_command_risk
from hartley_agent.tools import (
    dispatch_tool,
    execute_bash,
    get_system_info,
    read_file,
)
from hartley_agent.ui import format_markdown


class TestSafetyAssessment(unittest.TestCase):
    def test_safe_commands(self):
        safe_cases = [
            "ls -la",
            "pwd",
            "cat README.md",
            "git status",
            "git diff HEAD~1",
            "git log -n 5",
            "grep -rn 'foo' .",
            "echo 'hello world'",
            "which python3",
            "ps aux | grep node",
            "sw_vers",
            "df -h",
        ]
        for cmd in safe_cases:
            report = assess_command_risk(cmd)
            self.assertEqual(
                report.level,
                RiskLevel.SAFE,
                f"Expected SAFE for '{cmd}', got {report.level} ({report.reason})",
            )

    def test_moderate_commands(self):
        mod_cases = [
            "mkdir -p new_folder",
            "touch test.txt",
            "git add .",
            "git commit -m 'feat: update'",
            "npm install",
            "brew install jq",
            "echo 'hello' > output.txt",
        ]
        for cmd in mod_cases:
            report = assess_command_risk(cmd)
            self.assertEqual(
                report.level,
                RiskLevel.MODERATE,
                f"Expected MODERATE for '{cmd}', got {report.level} ({report.reason})",
            )

    def test_dangerous_commands(self):
        danger_cases = [
            "rm -rf /",
            "rm -rf ~",
            "rm -rf *",
            "sudo rm -f something",
            "sudo apt-get install",
            "dd if=/dev/zero of=/dev/disk1",
            "chmod -R 777 /var",
            "diskutil eraseDisk APFS MyDisk /dev/disk2",
            ":(){ :|:& };:",
            "kill -9 -1",
        ]
        for cmd in danger_cases:
            report = assess_command_risk(cmd)
            self.assertEqual(
                report.level,
                RiskLevel.DANGEROUS,
                f"Expected DANGEROUS for '{cmd}', got {report.level} ({report.reason})",
            )


class TestTools(unittest.TestCase):
    def test_get_system_info(self):
        info = get_system_info()
        self.assertIn("os", info)
        self.assertIn("shell", info)
        self.assertIn("cwd", info)
        self.assertIn("git", info)

    def test_execute_bash(self):
        result = execute_bash("echo 'hartley_test_ok'")
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("hartley_test_ok", result["stdout"])

    def test_execute_bash_error(self):
        result = execute_bash("non_existent_command_xyz123")
        self.assertNotEqual(result["exit_code"], 0)
        self.assertTrue(bool(result["stderr"]))

    def test_read_file(self):
        res = read_file("README.md", max_lines=500)
        self.assertIn("content", res)
        self.assertFalse(res.get("truncated", False))

        # Test truncated case
        res_trunc = read_file("README.md", max_lines=2)
        self.assertTrue(res_trunc.get("truncated", False))
        self.assertEqual(res_trunc.get("total_lines_read"), 2)

    def test_read_missing_file(self):
        res = read_file("this_file_does_not_exist_xyz.txt")
        self.assertIn("error", res)

    def test_dispatch_tool(self):
        res = dispatch_tool("execute_bash", {"command": "echo 'dispatched'"})
        self.assertEqual(res["exit_code"], 0)
        self.assertIn("dispatched", res["stdout"])

    def test_interactive_command_detection(self):
        from hartley_agent.tools import is_interactive_command
        self.assertTrue(is_interactive_command("ssh user@server"))
        self.assertTrue(is_interactive_command("ssh docker-mac"))
        self.assertTrue(is_interactive_command("ssh -i key.pem user@server"))
        self.assertTrue(is_interactive_command("docker exec -it my_container bash"))
        self.assertTrue(is_interactive_command("screen /dev/tty0"))
        self.assertTrue(is_interactive_command("top"))
        self.assertTrue(is_interactive_command("sudo htop"))
        self.assertTrue(is_interactive_command("vi /etc/hosts"))
        self.assertTrue(is_interactive_command("nano file.txt"))
        # Non-interactive remote commands should be False (allowed)
        self.assertFalse(is_interactive_command('ssh user@server "docker ps"'))
        self.assertFalse(is_interactive_command('ssh docker-mac docker ps'))
        self.assertFalse(is_interactive_command('ssh -p 22 docker-mac "docker logs immich"'))
        self.assertFalse(is_interactive_command("ls -la"))
        self.assertFalse(is_interactive_command("docker ps -a"))
        self.assertFalse(is_interactive_command("grep ssh file.txt"))
        self.assertFalse(is_interactive_command("cat nano.txt"))
        self.assertFalse(is_interactive_command("top -l 1"))

    def test_execute_bash_interactive_blocked(self):
        # Default allow_interactive=False should return exit code 1 with guidance
        result = execute_bash("ssh user@server")
        self.assertEqual(result["exit_code"], 1)
        self.assertIn("Interactive command blocked", result["stderr"])
        self.assertIn("do not run bare 'ssh <host>'", result["stderr"])

    @patch("os.system", return_value=0)
    def test_execute_bash_allow_interactive(self, mock_os_system):
        # When explicitly allowed, interactive commands run through os.system
        result = execute_bash("ssh user@server", allow_interactive=True)
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("interactive session completed in terminal", result["stdout"])
        mock_os_system.assert_called_once()


class TestConfig(unittest.TestCase):
    def test_config_get_set(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.dict(os.environ, {"HARTLEY_CONFIG_DIR": tmp_dir}):
                # Reset cached config dir
                import hartley_agent.config as cfg_mod
                cfg_mod._RESOLVED_CONFIG_DIR = None
                set_config_val("test_key", "test_val")
                self.assertEqual(get_config_val("test_key"), "test_val")
                cfg_mod._RESOLVED_CONFIG_DIR = None

    def test_api_key_resolution(self):
        from hartley_agent.config import get_api_key, get_api_key_source_description
        # 1. Explicit key (with quotes/whitespace stripping)
        self.assertEqual(get_api_key("explicit_123"), "explicit_123")
        self.assertEqual(get_api_key(' "quoted_key" '), "quoted_key")

        # 2. Environment variable
        with patch.dict(os.environ, {"GEMINI_API_KEY": "env_key_456"}):
            self.assertEqual(get_api_key(), "env_key_456")
            self.assertIn("$GEMINI_API_KEY", get_api_key_source_description())

    def test_key_cli_command(self):
        import tempfile
        from hartley_agent.cli import handle_key_cmd
        from hartley_agent.config import get_config_val
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.dict(os.environ, {"HARTLEY_CONFIG_DIR": tmp_dir, "GEMINI_API_KEY": ""}):
                import hartley_agent.config as cfg_mod
                cfg_mod._RESOLVED_CONFIG_DIR = None
                ret = handle_key_cmd(["AQ.test_new_auth_key_12345"])
                self.assertEqual(ret, 0)
                self.assertEqual(get_config_val("api_key"), "AQ.test_new_auth_key_12345")
                cfg_mod._RESOLVED_CONFIG_DIR = None


class TestGeminiClientHelpers(unittest.TestCase):
    def test_build_request_url_for_keys(self):
        client_aiza = GeminiClient(api_key="AIzaSyTestKey123")
        url_aiza = client_aiza._build_request_url("gemini-2.5-flash", "generateContent")
        self.assertIn("key=AIzaSyTestKey123", url_aiza)

        # New Google AI Studio auth keys (AQ.) must NOT be in query string
        client_aq = GeminiClient(api_key="AQ.Ab8RN6KTestKey")
        url_aq = client_aq._build_request_url("gemini-2.5-flash", "generateContent")
        self.assertNotIn("key=", url_aq)
        self.assertIn("/gemini-2.5-flash:generateContent", url_aq)

    def test_extract_text(self):
        resp = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Hello "},
                            {"text": "world!"},
                        ]
                    }
                }
            ]
        }
        self.assertEqual(extract_text_from_response(resp), "Hello world!")

    def test_extract_function_calls(self):
        resp = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "functionCall": {
                                    "name": "execute_bash",
                                    "args": {"command": "ls -la"},
                                }
                            }
                        ]
                    }
                }
            ]
        }
        calls = extract_function_calls(resp)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["name"], "execute_bash")
        self.assertEqual(calls[0]["args"]["command"], "ls -la")


class TestUIFormatting(unittest.TestCase):
    def test_format_markdown(self):
        md = "# Header 1\n## Header 2\n- Bullet item\n`inline_code`\n```bash\necho hello\n```"
        formatted = format_markdown(md)
        self.assertIn("echo hello", formatted)
        self.assertIn("Bullet item", formatted)


class TestAgentReActLoop(unittest.TestCase):
    def test_run_goal_tool_call_flow(self):
        # Mock Gemini client to return a function call, then a completion message
        mock_client = MagicMock()
        tool_call_resp = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "functionCall": {
                                    "name": "execute_bash",
                                    "args": {"command": "echo 'step1_complete'"},
                                }
                            }
                        ]
                    }
                }
            ]
        }
        final_resp = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Task finished successfully!"}]
                    }
                }
            ]
        }
        mock_client.generate_content.side_effect = [tool_call_resp, final_resp]

        agent = TerminalAgent(client=mock_client, auto_approve_safe=True, max_turns=5)

        # Run goal
        with patch("hartley_agent.agent.prompt_command_action", return_value="run"):
            agent.run_goal("Test multi-step task")

        # Verify client was called twice (turn 1 tool call, turn 2 completion)
        self.assertEqual(mock_client.generate_content.call_count, 2)


class TestRateLimitHandling(unittest.TestCase):
    def test_rate_limit_backoff(self):
        client = GeminiClient(api_key="test_key")

        # Mock urllib.request.urlopen to simulate 429 then 200
        mock_429 = MagicMock()
        mock_429.code = 429
        mock_429.read.return_value = json.dumps({"error": {"message": "Resource exhausted"}}).encode("utf-8")

        mock_200 = MagicMock()
        mock_200.read.return_value = json.dumps({
            "candidates": [{"content": {"parts": [{"text": "Success after retry"}]}}]
        }).encode("utf-8")

        http_error_429 = urllib.error.HTTPError(
            url="https://api", code=429, msg="Too Many Requests", hdrs={}, fp=mock_429
        )

        with patch("urllib.request.urlopen", side_effect=[http_error_429, mock_200]):
            with patch("time.sleep") as mock_sleep:
                resp = client.generate_content(contents=[{"role": "user", "parts": [{"text": "hi"}]}])
                self.assertIn("candidates", resp)
                mock_sleep.assert_called_once_with(3)


class TestMemory(unittest.TestCase):
    def test_window_memory_lifecycle(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.dict(os.environ, {"HARTLEY_CONFIG_DIR": tmp_dir}):
                import hartley_agent.config as cfg_mod
                cfg_mod._RESOLVED_CONFIG_DIR = None

                from hartley_agent.memory import WindowMemory, get_terminal_window_id
                win_id = get_terminal_window_id()
                self.assertTrue(bool(win_id))

                wm = WindowMemory(session_id="test_win_123", max_messages=4)
                self.assertEqual(wm.load_messages(), [])

                messages = [
                    {"role": "user", "parts": [{"text": "msg 1"}]},
                    {"role": "model", "parts": [{"text": "resp 1"}]},
                    {"role": "user", "parts": [{"text": "msg 2"}]},
                    {"role": "model", "parts": [{"text": "resp 2"}]},
                    {"role": "user", "parts": [{"text": "msg 3"}]},
                ]
                wm.save_messages(messages)
                loaded = wm.load_messages()
                self.assertEqual(len(loaded), 4)
                self.assertEqual(loaded[-1]["parts"][0]["text"], "msg 3")

                wm.clear()
                self.assertEqual(wm.load_messages(), [])
                cfg_mod._RESOLVED_CONFIG_DIR = None

    def test_global_memory_lifecycle(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.dict(os.environ, {"HARTLEY_CONFIG_DIR": tmp_dir}):
                import hartley_agent.config as cfg_mod
                cfg_mod._RESOLVED_CONFIG_DIR = None

                from hartley_agent.memory import GlobalMemory
                gm = GlobalMemory()
                self.assertEqual(gm.load(), [])

                entry = gm.add("Docker host IP is 192.168.1.1")
                self.assertEqual(entry["id"], 1)
                self.assertIn("Docker host IP", gm.format_for_prompt())

                gm.add("Prefer zsh")
                self.assertEqual(len(gm.load()), 2)

                gm.remove(1)
                self.assertEqual(len(gm.load()), 1)

                gm.clear()
                self.assertEqual(gm.load(), [])
                cfg_mod._RESOLVED_CONFIG_DIR = None

    def test_save_to_global_memory_tool(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.dict(os.environ, {"HARTLEY_CONFIG_DIR": tmp_dir}):
                import hartley_agent.config as cfg_mod
                cfg_mod._RESOLVED_CONFIG_DIR = None

                from hartley_agent.tools import dispatch_tool
                from hartley_agent.memory import GlobalMemory

                res = dispatch_tool("save_to_global_memory", {"fact": "My main repo is in ~/work"})
                self.assertEqual(res["status"], "saved")

                gm = GlobalMemory()
                items = gm.load()
                self.assertEqual(len(items), 1)
                self.assertEqual(items[0]["content"], "My main repo is in ~/work")
                cfg_mod._RESOLVED_CONFIG_DIR = None


class TestThemes(unittest.TestCase):
    def test_all_expected_themes_present(self):
        from hartley_agent.themes import THEMES, list_themes
        expected = [
            "modern",
            "hacker",
            "steampunk",
            "cyberpunk",
            "synthwave",
            "mono",
        ]
        themes = list_themes()
        self.assertEqual(len(themes), 6)
        for name in expected:
            self.assertIn(name, THEMES)
            theme = THEMES[name]
            self.assertEqual(theme.name, name)
            self.assertTrue(len(theme.display_name) > 0)
            self.assertTrue(len(theme.prompt_symbol) > 0)
            self.assertTrue(len(theme.spinner_frames) > 0)

    def test_get_theme_resolution(self):
        from hartley_agent.themes import get_theme
        th = get_theme("steampunk")
        self.assertEqual(th.name, "steampunk")

        th_upper = get_theme("HACKER")
        self.assertEqual(th_upper.name, "hacker")

        th_fallback = get_theme("non_existent_theme_xyz")
        self.assertEqual(th_fallback.name, "modern")

    def test_render_box_and_card(self):
        from hartley_agent.themes import get_theme
        for name in ["modern", "hacker", "steampunk", "cyberpunk", "synthwave", "mono"]:
            th = get_theme(name)
            card = th.render_card("echo 'hello'", risk_level="SAFE", risk_reason="Read-only")
            self.assertIn("echo 'hello'", card)
            self.assertIn("SAFE", card)

            banner = th.render_banner()
            self.assertTrue(len(banner) > 0)
            self.assertIn(th.banner_title, banner)

    def test_render_theme_gallery(self):
        from hartley_agent.themes import render_theme_gallery
        gallery = render_theme_gallery()
        self.assertIn("THEME GALLERY", gallery)
        for name in ["modern", "hacker", "steampunk", "cyberpunk", "synthwave", "mono"]:
            self.assertIn(name, gallery)

    def test_cli_theme_command(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.dict(os.environ, {"HARTLEY_CONFIG_DIR": tmp_dir}):
                import hartley_agent.config as cfg_mod
                cfg_mod._RESOLVED_CONFIG_DIR = None
                from hartley_agent.cli import handle_theme_cmd

                ret = handle_theme_cmd(["set", "steampunk"])
                self.assertEqual(ret, 0)
                self.assertEqual(cfg_mod.get_config_val("theme"), "steampunk")

                ret_direct = handle_theme_cmd(["cyberpunk"])
                self.assertEqual(ret_direct, 0)
                self.assertEqual(cfg_mod.get_config_val("theme"), "cyberpunk")

                ret_unknown = handle_theme_cmd(["set", "invalid_theme_name"])
                self.assertEqual(ret_unknown, 1)

                cfg_mod._RESOLVED_CONFIG_DIR = None


class TestAnimations(unittest.TestCase):
    def test_thinking_visualizer(self):
        from hartley_agent.animations import ThinkingVisualizer
        # Test enter/exit without error in non-interactive environment
        with ThinkingVisualizer("Testing thought process"):
            pass

    def test_tool_visualizer(self):
        from hartley_agent.animations import ToolExecutionVisualizer
        with ToolExecutionVisualizer("ls -la"):
            pass

    def test_boot_sequences(self):
        from hartley_agent.animations import play_boot_sequence
        from hartley_agent.themes import get_theme
        for name in ["modern", "hacker", "steampunk", "cyberpunk", "synthwave", "mono"]:
            th = get_theme(name)
            # Must run cleanly without raising exception
            play_boot_sequence(th)

    def test_cli_anim_command(self):
        import tempfile
        from hartley_agent.cli import handle_anim_cmd
        from hartley_agent.config import is_animations_enabled
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.dict(os.environ, {"HARTLEY_CONFIG_DIR": tmp_dir}):
                import hartley_agent.config as cfg_mod
                cfg_mod._RESOLVED_CONFIG_DIR = None

                self.assertEqual(handle_anim_cmd(["on"]), 0)
                self.assertTrue(is_animations_enabled())

                self.assertEqual(handle_anim_cmd(["off"]), 0)
                self.assertFalse(is_animations_enabled())

                self.assertEqual(handle_anim_cmd(["toggle"]), 0)
                self.assertTrue(is_animations_enabled())

                self.assertEqual(handle_anim_cmd([]), 0)
                self.assertEqual(handle_anim_cmd(["invalid"]), 1)

                cfg_mod._RESOLVED_CONFIG_DIR = None

    def test_showcase_functions(self):
        from hartley_agent.showcase import (
            run_showcase,
            showcase_all_themes,
            showcase_single_theme,
        )
        # Test individual theme showcase without blocking
        showcase_single_theme("hacker", interactive=False, speed=0.1, force_animations=False)
        showcase_single_theme("steampunk", interactive=False, speed=0.1, force_animations=False)

        # Test showcase all themes in non-interactive mode
        showcase_all_themes(interactive=False, speed=0.1, force_animations=False)

        # Test CLI dispatcher
        self.assertEqual(run_showcase(["modern"]), 0)
        self.assertEqual(run_showcase(["invalid_name_xyz"]), 1)

    def test_cli_showcase_routing(self):
        from hartley_agent.cli import main
        # Test routing through main CLI
        with patch("hartley_agent.showcase.showcase_single_theme") as mock_single:
            ret = main(["showcase", "cyberpunk"])
            self.assertEqual(ret, 0)
            mock_single.assert_called_once()

        with patch("hartley_agent.showcase.showcase_all_themes") as mock_all:
            ret = main(["showcase"])
            self.assertEqual(ret, 0)
            mock_all.assert_called_once()

        with patch("hartley_agent.showcase.showcase_single_theme") as mock_theme_sc:
            ret = main(["theme", "showcase", "synthwave"])
            self.assertEqual(ret, 0)
            mock_theme_sc.assert_called_once()


if __name__ == "__main__":
    unittest.main()
