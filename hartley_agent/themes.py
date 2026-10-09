"""Theme system for Hartley terminal UI and styling."""

import os
from typing import Dict, List, Optional


class Theme:
    """Represents a visual styling theme for Hartley."""

    def __init__(
        self,
        name: str,
        display_name: str,
        description: str,
        prompt_symbol: str,
        primary: str,
        secondary: str,
        accent: str,
        success: str,
        warning: str,
        danger: str,
        muted: str,
        text: str,
        box_tl: str,
        box_tr: str,
        box_bl: str,
        box_br: str,
        box_h: str,
        box_v: str,
        spinner_frames: List[str],
        banner_title: str,
        banner_tagline: str,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.prompt_symbol = prompt_symbol

        # ANSI Colors
        self.primary = primary
        self.secondary = secondary
        self.accent = accent
        self.success = success
        self.warning = warning
        self.danger = danger
        self.muted = muted
        self.text = text

        # Box characters
        self.box_tl = box_tl
        self.box_tr = box_tr
        self.box_bl = box_bl
        self.box_br = box_br
        self.box_h = box_h
        self.box_v = box_v

        # Animation
        self.spinner_frames = spinner_frames

        # Banner text
        self.banner_title = banner_title
        self.banner_tagline = banner_tagline

    def render_banner(self) -> str:
        """Render themed startup banner."""
        r = "\033[0m"
        b = "\033[1m"
        w = 64
        top = f"{self.primary}{self.box_tl}{self.box_h * (w - 2)}{self.box_tr}{r}"
        bot = f"{self.primary}{self.box_bl}{self.box_h * (w - 2)}{self.box_br}{r}"
        
        title_line = f"{self.primary}{self.box_v}{r}  {b}{self.accent}{self.banner_title}{r}"
        pad1 = " " * (w - 4 - len(self.banner_title))
        line1 = f"{title_line}{pad1}{self.primary}{self.box_v}{r}"

        tag_line = f"{self.primary}{self.box_v}{r}  {self.muted}{self.banner_tagline}{r}"
        pad2 = " " * (w - 4 - len(self.banner_tagline))
        line2 = f"{tag_line}{pad2}{self.primary}{self.box_v}{r}"

        return f"{top}\n{line1}\n{line2}\n{bot}"

    def render_card(self, command: str, risk_level: str = "MODERATE", risk_reason: str = "") -> str:
        """Render a formatted command box."""
        r = "\033[0m"
        b = "\033[1m"
        w = 64

        if risk_level == "DANGEROUS":
            border = self.danger
            badge = f"\033[41m\033[97m{b} [!] DANGEROUS {r} {self.danger}{risk_reason}{r}"
        elif risk_level == "SAFE":
            border = self.success
            badge = f"{self.success}{b}[OK] SAFE (Read-Only){r}"
        else:
            border = self.warning
            badge = f"{self.warning}{b}[!] MODERATE{r} {self.muted}{risk_reason}{r}"

        top = f"{border}{self.box_tl}{self.box_h * (w - 2)}{self.box_tr}{r}"
        mid1 = f"{border}{self.box_v}{r}  {b}Suggested Command:{r}"
        mid2 = f"{border}{self.box_v}{r}    {b}{self.accent}$ {command}{r}"
        mid3 = f"{border}{self.box_v}{r}  {badge}"
        bot = f"{border}{self.box_bl}{self.box_h * (w - 2)}{self.box_br}{r}"

        return f"\n{top}\n{mid1}\n{mid2}\n{mid3}\n{bot}"


# ANSI Code Constants (with 256-color palette extensions)
R = "\033[0m"
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Standard / 256 colors
CYAN_BRIGHT = "\033[96m"
GREEN_BRIGHT = "\033[92m"
YELLOW_BRIGHT = "\033[93m"
RED_BRIGHT = "\033[91m"
GRAY_MUTED = "\033[90m"
WHITE_BRIGHT = "\033[97m"

# Hacker Matrix Lime
MATRIX_GREEN = "\033[38;5;46m"
MATRIX_DARK = "\033[38;5;28m"
MATRIX_BRIGHT = "\033[38;5;118m"

# Steampunk Brass & Copper
COPPER = "\033[38;5;178m"
BRASS = "\033[38;5;136m"
BRONZE = "\033[38;5;94m"
PARCHMENT = "\033[38;5;223m"

# Cyberpunk Neon
NEON_PINK = "\033[38;5;198m"
NEON_CYAN = "\033[38;5;51m"
NEON_PURPLE = "\033[38;5;141m"

# Synthwave Outrun
SYNTH_VIOLET = "\033[38;5;135m"
SYNTH_CORAL = "\033[38;5;204m"
SYNTH_SUN = "\033[38;5;220m"


THEMES: Dict[str, Theme] = {
    "modern": Theme(
        name="modern",
        display_name="Modern Glass",
        description="Clean, refined macOS developer aesthetics with electric cyan accents",
        prompt_symbol="hartley >> ",
        primary=CYAN_BRIGHT,
        secondary="\033[94m",
        accent=CYAN_BRIGHT,
        success=GREEN_BRIGHT,
        warning=YELLOW_BRIGHT,
        danger=RED_BRIGHT,
        muted=GRAY_MUTED,
        text=WHITE_BRIGHT,
        box_tl="╭",
        box_tr="╮",
        box_bl="╰",
        box_br="╯",
        box_h="─",
        box_v="│",
        spinner_frames=["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
        banner_title="[::] HARTLEY  │  Modern Gemini Terminal Agent",
        banner_tagline="Autonomous pair programmer & terminal agent",
    ),
    "hacker": Theme(
        name="hacker",
        display_name="Hacker Matrix",
        description="Cyberspace deck with high-contrast Matrix lime green phosphor",
        prompt_symbol="root@hartley:# ",
        primary=MATRIX_GREEN,
        secondary=MATRIX_DARK,
        accent=MATRIX_BRIGHT,
        success=MATRIX_GREEN,
        warning=YELLOW_BRIGHT,
        danger=RED_BRIGHT,
        muted=MATRIX_DARK,
        text=MATRIX_BRIGHT,
        box_tl="+",
        box_tr="+",
        box_bl="+",
        box_br="+",
        box_h="-",
        box_v="|",
        spinner_frames=["[01001]", "[10110]", "[00101]", "[11010]", "[01110]", "[10001]"],
        banner_title="/* HARTLEY CYBERDECK // ROOT ACCESS GRANTED */",
        banner_tagline="Bypassing system heuristics... Kernel hooks active.",
    ),
    "steampunk": Theme(
        name="steampunk",
        display_name="Steampunk Clockwork",
        description="Victorian burnished brass, copper tubing, pressure gauges, and cogs",
        prompt_symbol="[STEAM] HARTLEY >> ",
        primary=COPPER,
        secondary=BRONZE,
        accent=BRASS,
        success=BRASS,
        warning=COPPER,
        danger=RED_BRIGHT,
        muted=BRONZE,
        text=PARCHMENT,
        box_tl="⟦",
        box_tr="⟧",
        box_bl="⟦",
        box_br="⟧",
        box_h="═",
        box_v="║",
        spinner_frames=["[-]", "[\\]", "[|]", "[/]"],
        banner_title="[+] HARTLEY & CO. DIFFERENCE ENGINE NO. 2",
        banner_tagline="Steam Pressure: 140 PSI // Clockwork Automaton Active",
    ),
    "cyberpunk": Theme(
        name="cyberpunk",
        display_name="Cyberpunk Neon",
        description="Night City neon pink and turquoise electric synth aesthetics",
        prompt_symbol="CYBER//DECK>> ",
        primary=NEON_PINK,
        secondary=NEON_PURPLE,
        accent=NEON_CYAN,
        success=NEON_CYAN,
        warning=YELLOW_BRIGHT,
        danger=RED_BRIGHT,
        muted=NEON_PURPLE,
        text=WHITE_BRIGHT,
        box_tl="◤",
        box_tr="◥",
        box_bl="◣",
        box_br="◢",
        box_h="━",
        box_v="┃",
        spinner_frames=["◢", "◣", "◤", "◥"],
        banner_title="// NETRUNNER ICE-BREAKER // HARTLEY OS 2077",
        banner_tagline="Neural link calibrated. Data stream flowing.",
    ),
    "synthwave": Theme(
        name="synthwave",
        display_name="Synthwave Outrun",
        description="1984 arcade sunset violet, radiant coral, and VHS gridlines",
        prompt_symbol="OUTRUN ~> ",
        primary=SYNTH_VIOLET,
        secondary=SYNTH_CORAL,
        accent=SYNTH_SUN,
        success=SYNTH_SUN,
        warning=SYNTH_CORAL,
        danger=RED_BRIGHT,
        muted=SYNTH_VIOLET,
        text=WHITE_BRIGHT,
        box_tl="~",
        box_tr="~",
        box_bl="~",
        box_br="~",
        box_h="═",
        box_v="║",
        spinner_frames=["═", "╧", "═", "╤"],
        banner_title="// HARTLEY // OUTRUN 1984 VINTAGE GRID",
        banner_tagline="Cruising through the vector sunset neon expressway.",
    ),
    "mono": Theme(
        name="mono",
        display_name="Monochrome Minimal",
        description="Distraction-free typographic minimalism with pure white and charcoal",
        prompt_symbol="h: ",
        primary=WHITE_BRIGHT,
        secondary=GRAY_MUTED,
        accent=WHITE_BRIGHT,
        success=WHITE_BRIGHT,
        warning=GRAY_MUTED,
        danger=BOLD + WHITE_BRIGHT,
        muted=GRAY_MUTED,
        text=WHITE_BRIGHT,
        box_tl="+",
        box_tr="+",
        box_bl="+",
        box_br="+",
        box_h="-",
        box_v="|",
        spinner_frames=["·  ", "·· ", "···", "·· "],
        banner_title="HARTLEY // MINIMAL TERMINAL INTERFACE",
        banner_tagline="Focus-driven system automation.",
    ),
}


def get_theme(name: Optional[str] = None) -> Theme:
    """Retrieve theme by name, or from config if not specified."""
    if not name:
        from .config import get_config_val
        name = get_config_val("theme", "modern")

    clean_name = str(name).strip().lower()
    return THEMES.get(clean_name, THEMES["modern"])


def list_themes() -> List[Theme]:
    """Return all available themes."""
    return list(THEMES.values())


def render_theme_gallery() -> str:
    """Render a visual preview showcase of all available themes."""
    lines = []
    lines.append("\033[1m\033[96m╔══════════════════════════════════════════════════════════════╗\033[0m")
    lines.append("\033[1m\033[96m║                 [+] HARTLEY THEME GALLERY                    ║\033[0m")
    lines.append("\033[1m\033[96m╚══════════════════════════════════════════════════════════════╝\033[0m\n")

    from .config import get_config_val
    current_name = get_config_val("theme", "modern")

    for th in THEMES.values():
        active_badge = " \033[1;92m(ACTIVE)\033[0m" if th.name == current_name else ""
        spinner_str = " ".join(th.spinner_frames)
        lines.append(f"{th.primary}●\033[0m \033[1m{th.display_name}\033[0m [\033[96m{th.name}\033[0m]{active_badge}")
        lines.append(f"  \033[90mDescription:\033[0m {th.description}")
        lines.append(f"  \033[90mPrompt:\033[0m      {th.primary}{th.prompt_symbol}\033[0m")
        lines.append(f"  \033[90mPalette:\033[0m     {th.primary}■ Primary\033[0m  {th.accent}■ Accent\033[0m  {th.secondary}■ Secondary\033[0m  {th.success}■ Success\033[0m  {th.warning}■ Warn\033[0m  {th.danger}■ Danger\033[0m")
        lines.append(f"  \033[90mSpinners:\033[0m    {th.primary}{spinner_str}\033[0m")
        lines.append(f"  \033[90mSample Box:\033[0m  {th.primary}{th.box_tl}{th.box_h*12}{th.box_tr}\033[0m {th.accent}{th.banner_title[:28]}...\033[0m {th.primary}{th.box_bl}{th.box_h*12}{th.box_br}\033[0m")
        lines.append("")

    lines.append("\033[1;96mExperience Live Animations & Boot Sequences:\033[0m")
    lines.append("  \033[1mhartley showcase\033[0m          Tour all themes with live animations and visualizers")
    lines.append("  \033[1mhartley showcase <name>\033[0m   Showcase a specific theme (e.g. 'hartley showcase cyberpunk')")
    lines.append("\n\033[90mTo switch themes directly, run:\033[0m \033[1;96mhartley theme set <name>\033[0m")
    lines.append("\033[90mInside the REPL, type:\033[0m          \033[1;96m/theme <name>\033[0m or \033[1;96m/showcase\033[0m")
    return "\n".join(lines)
