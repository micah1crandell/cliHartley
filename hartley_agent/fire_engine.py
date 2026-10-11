"""
Hartley Cinematic Fire & Thermal Loop Engine.

Renders a 30-second multi-act terminal animation at startup or on-demand:
- Act I:   Quantum Matrix Genesis (Matrix rain, binary decode, boot assembly)
- Act II:  Aurora Plasma Wave (Iridescent RGB waves, crystalline shimmer)
- Act III: Thermal Ground Ignition (Flame tongues, rising ember draft, burning chars)
- Act IV:  Inferno Meltdown & CRT Heat Haze (Full thermal storm, jitter displacement)
- Act V:   Supernova Blast & Ash Dissolve (Radial blast wave, crumbling ash)
- Act VI:  Lightning Arcs & Crystalline Rebirth (Electric arcs, laser grid reconstruction)
"""

import atexit
import math
import os
import random
import shutil
import signal
import sys
import time
from typing import Optional

try:
    import select
    import termios
    import tty
    WINDOWS = False
except ImportError:
    import msvcrt
    WINDOWS = True

# Terminal ANSI control codes
C_RESET = "\033[0m"
C_HIDE = "\033[?25l"
C_SHOW = "\033[?25h"
C_HOME = "\033[H"
C_CLEAR = "\033[2J"
C_ALT_ON = "\033[?1049h"
C_ALT_OFF = "\033[?1049l"


def rgb_fg(r: int, g: int, b: int) -> str:
    """Return 24-bit truecolor foreground ANSI code."""
    return f"\033[38;2;{max(0, min(255, int(r)))};{max(0, min(255, int(g)))};{max(0, min(255, int(b)))}m"


# Artwork Definitions
LOCK_ART = [
    "      ▄▄██████▄▄      ",
    "   ▄███▀▀    ▀▀███▄   ",
    "  ███   ▄▄▄▄▄▄   ███  ",
    " ███   ██    ██   ███ ",
    " ███   ██ ▀▀ ██   ███ ",
    " ███   ██    ██   ███ ",
    " ███   ▀██████▀   ███ ",
    " ███              ███ ",
    "  ▀███▄▄    ▄▄███▀    ",
    "    ▀▀████████▀▀      ",
]

HARTLEY_BANNER = [
    "█   █   ███   ████   █████  █      █████  █   █",
    "█   █  █   █  █   █    █    █      █       █ █ ",
    "█████  █████  ████     █    █      ████     █  ",
    "█   █  █   █  █  █     █    █      █        █  ",
    "█   █  █   █  █   █    █    █████  █████    █  ",
]

SUBTITLE_TEXT = "Z E R O   T R U S T"

TELEMETRY_TEMPLATE = [
    ("fastfetch // telemetry", None),
    ("Hartley Core Defense Matrix", None),
    ("", None),
    ("◆ Product", "Hartley Core Lock 2.5"),
    ("◆ Doctrine", "Zero Trust // Verified"),
    ("◆ Policy", "Deny by Default • Enforce All"),
    ("◆ Topology", "Ringfenced Mesh Matrix"),
    ("◆ Endpoints", "Linux • macOS • Windows"),
    ("◆ Latency", "{latency} ms • verified"),
    ("", None),
    ("── Platform Defenses ──", None),
    ("Ringfencing", "{ringfence}"),
    ("Network Ctrl", "{network}"),
    ("Storage Fence", "{storage}"),
    ("Elevation", "{elevation}"),
    ("", None),
    ("── Zero Trust Posture ──", None),
    ("Applications", "HOMELISTED"),
    ("Storage Layer", "POLICY-LOCKED"),
    ("Unknown Code", "IMMEDIATE-DROP"),
    ("Threat Meter", "{threat_bar}"),
    ("Buffer Purge", "{purge_status}"),
    ("", None),
    ("Zero Compromise. Infinite Defense.", None),
]

FIRE_CHARS = ['#', '*', '%', '░', '▓', '█', '@', '&', '▲', '§']
GLITCH_CHARS = ['0', '1', 'X', 'Z', '?', '/', '\\', '!', '$', '%', '&', '#', 'Ø', 'Ξ']
EMBER_CHARS = ['*', '+', '·', '•', '^', '°', '▲', '■', '✦']
LIGHTNING_CHARS = ['/', '\\', '|', '-', '⚡', '+', '*', 'x']
MATRIX_CHARS = ['0', '1', '2', '8', 'A', 'Z', 'F', '9', 'X', 'Y', 'λ', 'π', 'Ω']

ACTS = [
    (0.0, 4.5, "ACT I: QUANTUM MATRIX GENESIS"),
    (4.5, 9.0, "ACT II: AURORA PLASMA WAVE"),
    (9.0, 14.0, "ACT III: THERMAL GROUND IGNITION"),
    (14.0, 19.5, "ACT IV: INFERNO MELTDOWN & HEAT HAZE"),
    (19.5, 24.0, "ACT V: SUPERNOVA BLAST & ASH DISSOLVE"),
    (24.0, 30.0, "ACT VI: LIGHTNING REBIRTH & CRYSTAL LOCK"),
]
TOTAL_LOOP_TIME = 30.0


class Ember:
    """Rising buoyant fire spark particle."""
    def __init__(self, x: float, y: float, vx: float, vy: float, life: float, char: str):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.char = char

    def update(self, dt: float):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy -= 5.0 * dt
        self.vx += (random.random() - 0.5) * 4.5 * dt
        self.life -= dt

    def get_color(self) -> str:
        ratio = max(0.0, min(1.0, self.life / self.max_life))
        if ratio > 0.75:
            return rgb_fg(255, 255, 240)
        elif ratio > 0.45:
            return rgb_fg(255, 180, 30)
        elif ratio > 0.20:
            return rgb_fg(235, 50, 15)
        else:
            return rgb_fg(120, 50, 50)


class AshParticle:
    """Falling ash cinder particle created during supernova dissolve."""
    def __init__(self, x: float, y: float, vx: float, vy: float, life: float, char: str):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.char = char

    def update(self, dt: float):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 1.8 * dt
        self.vx += math.sin(self.life * 6.0) * 1.5 * dt
        self.life -= dt

    def get_color(self) -> str:
        ratio = max(0.0, min(1.0, self.life / self.max_life))
        g = int(50 + 90 * ratio)
        r = int(70 + 80 * ratio)
        b = int(50 + 70 * ratio)
        return rgb_fg(r, g, b)


class MatrixColumn:
    """Falling binary rain column in the background during Act I."""
    def __init__(self, x: int, max_y: int):
        self.x = x
        self.max_y = max_y
        self.y = random.uniform(-max_y, 0)
        self.speed = random.uniform(8.0, 18.0)
        self.length = random.randint(4, 12)

    def update(self, dt: float):
        self.y += self.speed * dt
        if self.y - self.length > self.max_y:
            self.y = random.uniform(-10, -2)
            self.speed = random.uniform(8.0, 18.0)


class HartleyRasterGrid:
    """Combines lock emblem and Hartley word art into a discrete 2D cell grid."""
    def __init__(self):
        self.grid = []
        self.width = 0
        self.height = 0
        self.lock_cells = []
        self.banner_cells = []
        self.subtitle_cells = []
        self._build_grid()

    def _build_grid(self):
        lines = []
        banner_w = max(len(l) for l in HARTLEY_BANNER)
        lock_w = max(len(l) for l in LOCK_ART)
        lock_pad = max(0, (banner_w - lock_w) // 2)

        lock_start_row = 0
        for l in LOCK_ART:
            lines.append(" " * lock_pad + l)
        lock_end_row = len(lines)

        lines.append("")

        banner_start_row = len(lines)
        for l in HARTLEY_BANNER:
            lines.append(l)
        banner_end_row = len(lines)

        lines.append("")

        sub_pad = max(0, (banner_w - len(SUBTITLE_TEXT)) // 2)
        sub_start_row = len(lines)
        lines.append(" " * sub_pad + SUBTITLE_TEXT)
        sub_end_row = len(lines)

        self.height = len(lines)
        self.width = max(len(l) for l in lines)

        for r, line in enumerate(lines):
            for c, char in enumerate(line):
                if char != ' ':
                    if lock_start_row <= r < lock_end_row:
                        part = "lock"
                        self.lock_cells.append((c, r, char))
                    elif banner_start_row <= r < banner_end_row:
                        part = "banner"
                        self.banner_cells.append((c, r, char))
                    else:
                        part = "subtitle"
                        self.subtitle_cells.append((c, r, char))

                    self.grid.append((c, r, char, part))


def get_current_act_info(t: float) -> tuple:
    """Returns (act_index, act_name, progress_in_act)."""
    t_mod = t % TOTAL_LOOP_TIME
    for idx, (start_t, end_t, name) in enumerate(ACTS):
        if start_t <= t_mod < end_t or idx == len(ACTS) - 1:
            progress = (t_mod - start_t) / max(0.01, end_t - start_t)
            return idx, name, min(1.0, max(0.0, progress))
    return 0, ACTS[0][2], 0.0


def cleanup_screen():
    """Restores cursor, colors, and original terminal screen buffer."""
    try:
        sys.stdout.write(f"{C_SHOW}{C_RESET}{C_ALT_OFF}\n")
        sys.stdout.flush()
    except Exception:
        pass


def check_key():
    """Non-blocking keyboard reader."""
    if WINDOWS:
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            try:
                return ch.decode('utf-8', errors='ignore')
            except Exception:
                return None
        return None
    else:
        rlist, _, _ = select.select([sys.stdin], [], [], 0)
        if rlist:
            return sys.stdin.read(1)
        return None


def get_matrix_color(intensity: float) -> str:
    if intensity > 0.88:
        return rgb_fg(220, 255, 220)
    elif intensity > 0.5:
        return rgb_fg(34, 197, 94)
    elif intensity > 0.2:
        return rgb_fg(22, 101, 52)
    else:
        return rgb_fg(10, 45, 20)


def get_aurora_color(x_norm: float, y_norm: float, phase: float) -> str:
    wave = (x_norm * 0.9 + y_norm * 0.85 - phase * 0.6) % 1.0
    r = int(50 + 190 * math.sin(wave * math.pi * 2))
    g = int(195 + 60 * math.cos(wave * math.pi * 2))
    b = int(220 + 35 * math.sin(wave * math.pi * 2 + 1.8))
    return rgb_fg(r, g, b)


def get_fire_color(intensity: float) -> str:
    if intensity > 0.85:
        return rgb_fg(255, 255, 255)
    elif intensity > 0.60:
        return rgb_fg(255, 235, 90)
    elif intensity > 0.35:
        return rgb_fg(249, 115, 22)
    elif intensity > 0.15:
        return rgb_fg(220, 38, 38)
    else:
        return rgb_fg(130, 25, 25)


def get_lightning_color() -> str:
    palette = [
        rgb_fg(255, 255, 255),
        rgb_fg(191, 219, 254),
        rgb_fg(96, 165, 250),
        rgb_fg(34, 211, 238),
    ]
    return random.choice(palette)


def get_gold_rebirth_color(x_norm: float, shimmer: float) -> str:
    dist = abs(x_norm - shimmer)
    if dist < 0.08:
        return rgb_fg(255, 255, 255)
    elif dist < 0.22:
        return rgb_fg(251, 191, 36)
    else:
        return rgb_fg(16, 185, 129)


def run_cinematic_animation(max_duration: Optional[float] = None, is_interactive_boot: bool = True) -> None:
    """
    Renders the 30-second thermal & cyber loop animation.
    
    Args:
        max_duration: Optional maximum time in seconds before auto-exiting to prompt.
        is_interactive_boot: If True, any keypress (Enter, Space, Esc, etc.) immediately exits
                             so the user can start using Hartley.
    """
    if not (sys.stdout.isatty()):
        return

    # Setup terminal alternate screen
    sys.stdout.write(f"{C_ALT_ON}{C_HIDE}{C_CLEAR}")
    sys.stdout.flush()

    orig_settings = None
    if not WINDOWS:
        try:
            orig_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        except Exception:
            pass

    raster = HartleyRasterGrid()
    center_lock_x = raster.width // 2
    center_lock_y = 5

    embers = []
    ash_particles = []
    matrix_cols = []

    loop_time = 0.0
    start_wall_time = time.time()
    last_frame_time = time.time()
    is_paused = False
    manual_blast = 0.0
    fps_sample_time = time.time()
    fps_frame_count = 0
    display_fps = 30

    try:
        while True:
            now = time.time()
            dt = min(now - last_frame_time, 0.08)
            last_frame_time = now

            fps_frame_count += 1
            if now - fps_sample_time >= 0.5:
                display_fps = int(fps_frame_count / (now - fps_sample_time))
                fps_frame_count = 0
                fps_sample_time = now

            # Check max duration timeout if specified
            if max_duration is not None and (now - start_wall_time) >= max_duration:
                break

            # Handle user input
            raw_key = check_key()
            if raw_key is not None:
                key = raw_key.lower()
                if is_interactive_boot:
                    # During startup boot sequence: Enter, Space, Q, Escape, or any key proceeds to prompt!
                    if raw_key in ('\n', '\r', ' ', 'q', '\x1b', 'c'):
                        break
                    elif key == 'f':
                        loop_time = 14.1  # Fast-forward to Inferno
                    elif key in ('1', '2', '3', '4', '5', '6'):
                        target_act = int(key) - 1
                        loop_time = ACTS[target_act][0]
                    else:
                        # Any other key also smoothly transitions to Hartley prompt
                        break
                else:
                    # In dedicated loop mode: full playback controls
                    if key == 'q':
                        break
                    elif raw_key == ' ':
                        manual_blast = 1.0
                    elif key == 'f':
                        loop_time = 14.1
                    elif key == 'r':
                        loop_time = 0.0
                        embers.clear()
                        ash_particles.clear()
                    elif key == 'p':
                        is_paused = not is_paused
                    elif key in ('1', '2', '3', '4', '5', '6'):
                        target_act = int(key) - 1
                        loop_time = ACTS[target_act][0]
                        embers.clear()
                        ash_particles.clear()

            if not is_paused:
                loop_time = (loop_time + dt) % TOTAL_LOOP_TIME
                if manual_blast > 0:
                    manual_blast = max(0.0, manual_blast - dt * 1.5)

            current_time = loop_time
            act_idx, act_name, act_prog = get_current_act_info(current_time)

            term_w, term_h = shutil.get_terminal_size((96, 26))
            show_telemetry = term_w >= 92 and term_h >= 24

            if len(matrix_cols) < term_w // 4:
                matrix_cols = [MatrixColumn(random.randint(0, term_w - 1), term_h) for _ in range(term_w // 4)]

            frame_chars = [[' ' for _ in range(term_w)] for _ in range(term_h)]
            frame_colors = [['' for _ in range(term_w)] for _ in range(term_h)]

            if show_telemetry:
                art_origin_x = max(2, (term_w // 2 - raster.width) // 2)
            else:
                art_origin_x = max(1, (term_w - raster.width) // 2)

            art_origin_y = max(1, (term_h - raster.height - 2) // 2)

            # Act I: Matrix Rain
            if act_idx == 0:
                for col in matrix_cols:
                    col.update(dt)
                    cx = col.x
                    if 0 <= cx < term_w:
                        head_y = int(col.y)
                        for trail in range(col.length):
                            cy = head_y - trail
                            if 0 <= cy < term_h:
                                intensity = 1.0 - (trail / col.length)
                                ch = random.choice(MATRIX_CHARS) if trail == 0 else random.choice(['0', '1', '.'])
                                frame_chars[cy][cx] = ch
                                frame_colors[cy][cx] = get_matrix_color(intensity)

            # Grid Rendering
            for (cx, cy, ch, part) in raster.grid:
                screen_x = art_origin_x + cx
                screen_y = art_origin_y + cy

                col_norm = cx / max(1, raster.width)
                row_norm = cy / max(1, raster.height)

                dx = cx - center_lock_x
                dy = (cy - center_lock_y) * 1.8
                dist_from_center = math.sqrt(dx * dx + dy * dy)

                draw_char = ch
                draw_color = ""
                skip_draw = False

                if act_idx == 0:
                    scan_line = act_prog * (raster.height + 4)
                    if cy > scan_line:
                        skip_draw = True
                    elif cy > scan_line - 2:
                        draw_char = random.choice(GLITCH_CHARS)
                        draw_color = rgb_fg(220, 255, 220)
                    else:
                        flicker = 0.9 + 0.1 * math.sin(current_time * 12.0 + cx * 0.4)
                        draw_color = rgb_fg(int(20 * flicker), int(220 * flicker), int(240 * flicker))

                elif act_idx == 1:
                    plasma_phase = current_time * 0.95
                    draw_color = get_aurora_color(col_norm, row_norm, plasma_phase)
                    if random.random() < 0.015:
                        draw_char = '✦'
                        draw_color = rgb_fg(255, 255, 255)

                elif act_idx == 2:
                    flame_height = act_prog * 1.3
                    heat_y = 1.0 - row_norm
                    wave = 0.2 * math.sin(cx * 0.6 + current_time * 7.0)
                    flame_level = flame_height + wave

                    if heat_y <= flame_level:
                        intensity = min(1.0, max(0.0, (flame_level - heat_y) * 1.5))
                        draw_color = get_fire_color(intensity)
                        if intensity > 0.4 and random.random() < 0.4:
                            draw_char = random.choice(FIRE_CHARS)

                        if random.random() < (0.09 * intensity) and len(embers) < 140:
                            embers.append(Ember(
                                x=screen_x + (random.random() - 0.5) * 1.5,
                                y=screen_y,
                                vx=(random.random() - 0.5) * 5.0,
                                vy=-(random.random() * 8.0 + 3.5),
                                life=random.uniform(0.7, 1.4),
                                char=random.choice(EMBER_CHARS)
                            ))
                    else:
                        draw_color = rgb_fg(240, 140, 30)

                elif act_idx == 3:
                    intensity = 0.5 + 0.5 * math.sin(current_time * 10.0 + cx * 0.4 + cy * 0.3)
                    draw_color = get_fire_color(intensity)
                    if intensity > 0.5:
                        draw_char = random.choice(FIRE_CHARS)

                    jitter_amp = math.sin(cy * 1.2 + current_time * 16.0)
                    if abs(jitter_amp) > 0.6 and random.random() < 0.35:
                        screen_x += 1 if jitter_amp > 0 else -1

                    if random.random() < 0.12 and len(embers) < 180:
                        embers.append(Ember(
                            x=screen_x + (random.random() - 0.5) * 2.0,
                            y=screen_y,
                            vx=(random.random() - 0.5) * 8.0,
                            vy=-(random.random() * 11.0 + 4.0),
                            life=random.uniform(0.6, 1.5),
                            char=random.choice(EMBER_CHARS)
                        ))

                elif act_idx == 4:
                    blast_radius = act_prog * 32.0
                    edge_thickness = 3.5

                    if dist_from_center < blast_radius - edge_thickness:
                        skip_draw = True
                        if random.random() < 0.03 and len(ash_particles) < 90:
                            ash_particles.append(AshParticle(
                                x=screen_x + (random.random() - 0.5) * 2,
                                y=screen_y,
                                vx=(random.random() - 0.5) * 2.5,
                                vy=random.uniform(0.5, 3.0),
                                life=random.uniform(1.2, 2.5),
                                char=random.choice(['·', '.', ',', ' '])
                            ))
                    elif abs(dist_from_center - blast_radius) <= edge_thickness:
                        draw_char = random.choice(['█', '▓', '#', '■', '*'])
                        draw_color = rgb_fg(255, 255, 255)
                    else:
                        draw_color = rgb_fg(220, 40, 20)
                        if random.random() < 0.2:
                            draw_char = random.choice(FIRE_CHARS)

                elif act_idx == 5:
                    rebuild_prog = act_prog * 1.2
                    if dist_from_center > rebuild_prog * 26.0:
                        if random.random() < 0.04:
                            draw_char = random.choice(LIGHTNING_CHARS)
                            draw_color = get_lightning_color()
                        else:
                            skip_draw = True
                    else:
                        shimmer_pos = ((current_time - 24.0) / 6.0) * 1.5 - 0.2
                        draw_color = get_gold_rebirth_color(col_norm, shimmer_pos)

                if manual_blast > 0:
                    blast_rad = (1.0 - manual_blast) * 28.0
                    if abs(dist_from_center - blast_rad) < 2.5:
                        draw_char = random.choice(FIRE_CHARS)
                        draw_color = rgb_fg(255, 255, 255)

                if not skip_draw and 0 <= screen_x < term_w and 0 <= screen_y < term_h:
                    frame_chars[screen_y][screen_x] = draw_char
                    frame_colors[screen_y][screen_x] = draw_color

            # Update Floating Particles
            for i in range(len(embers) - 1, -1, -1):
                emb = embers[i]
                emb.update(dt)
                if emb.life <= 0 or emb.y < 0 or emb.x < 0 or emb.x >= term_w or emb.y >= term_h:
                    embers.pop(i)
                else:
                    ex = int(emb.x)
                    ey = int(emb.y)
                    if 0 <= ey < term_h and 0 <= ex < term_w:
                        if frame_chars[ey][ex] in (' ', '·', '.'):
                            frame_chars[ey][ex] = emb.char
                            frame_colors[ey][ex] = emb.get_color()

            for i in range(len(ash_particles) - 1, -1, -1):
                ash = ash_particles[i]
                ash.update(dt)
                if ash.life <= 0 or ash.y >= term_h or ash.x < 0 or ash.x >= term_w:
                    ash_particles.pop(i)
                else:
                    ax = int(ash.x)
                    ay = int(ash.y)
                    if 0 <= ay < term_h and 0 <= ax < term_w:
                        if frame_chars[ay][ax] in (' ', '.'):
                            frame_chars[ay][ax] = ash.char
                            frame_colors[ay][ax] = ash.get_color()

            # Telemetry Pane
            if show_telemetry:
                pane_x = term_w // 2 + 2
                pane_y = max(1, (term_h - len(TELEMETRY_TEMPLATE) - 2) // 2)

                for r in range(1, term_h - 2):
                    sep_x = term_w // 2
                    if 0 <= r < term_h and 0 <= sep_x < term_w:
                        if act_idx in (2, 3):
                            frame_chars[r][sep_x] = "║"
                            frame_colors[r][sep_x] = rgb_fg(249, 115, 22)
                        elif act_idx == 4:
                            frame_chars[r][sep_x] = "│"
                            frame_colors[r][sep_x] = rgb_fg(220, 38, 38)
                        else:
                            frame_chars[r][sep_x] = "│"
                            frame_colors[r][sep_x] = rgb_fg(45, 65, 95)

                live_latency = f"{11 + int(4 * math.sin(current_time * 3.5))}"
                threat_blocks = int((act_idx / 5.0) * 8)
                threat_bar = f"[{'█' * threat_blocks}{'░' * (8 - threat_blocks)}]"

                if act_idx == 3:
                    ringfence_val = "THERMAL-ENGAGED"
                    network_val = "LOCKDOWN"
                    storage_val = "ISOLATED"
                    elevation_val = "REVOKED"
                    purge_val = "PURGING..."
                elif act_idx == 4:
                    ringfence_val = "CRITICAL-ALERT"
                    network_val = "DROPPED"
                    storage_val = "PURGED"
                    elevation_val = "NONE"
                    purge_val = "COMPLETE 100%"
                elif act_idx == 5:
                    ringfence_val = "RE-INITIALIZING"
                    network_val = "RE-ESTABLISHED"
                    storage_val = "VERIFIED"
                    elevation_val = "POLICY-SYNC"
                    purge_val = "CLEAN STATE"
                else:
                    ringfence_val = "ACTIVE"
                    network_val = "BLOCKED"
                    storage_val = "ENFORCED"
                    elevation_val = "JUST-IN-TIME"
                    purge_val = "READY"

                for idx, (label, val_tmpl) in enumerate(TELEMETRY_TEMPLATE):
                    cur_y = pane_y + idx
                    if not (0 <= cur_y < term_h):
                        continue

                    if val_tmpl is None:
                        full_str = label
                        if "telemetry" in label:
                            cur_col = rgb_fg(56, 189, 248)
                        elif "Defense" in label:
                            cur_col = rgb_fg(148, 163, 184)
                        elif "Defenses" in label or "Posture" in label:
                            cur_col = rgb_fg(94, 234, 212)
                        else:
                            cur_col = rgb_fg(148, 163, 184)

                        for c_i, ch in enumerate(full_str):
                            tx = pane_x + c_i
                            if tx < term_w:
                                frame_chars[cur_y][tx] = ch
                                frame_colors[cur_y][tx] = cur_col
                    else:
                        val = val_tmpl.format(
                            latency=live_latency,
                            ringfence=ringfence_val,
                            network=network_val,
                            storage=storage_val,
                            elevation=elevation_val,
                            threat_bar=threat_bar,
                            purge_status=purge_val,
                        )

                        key_col = rgb_fg(56, 189, 248)
                        if "ACTIVE" in val or "VERIFIED" in val or "CLEAN" in val:
                            val_col = rgb_fg(52, 211, 153)
                        elif "CRITICAL" in val or "PURGING" in val or "THERMAL" in val:
                            val_col = rgb_fg(239, 68, 68)
                        elif "LOCKDOWN" in val or "DROPPED" in val:
                            val_col = rgb_fg(245, 158, 11)
                        else:
                            val_col = rgb_fg(226, 232, 240)

                        key_str = f"{label:<16}"
                        val_str = f"{val}"

                        for c_i, ch in enumerate(key_str):
                            tx = pane_x + c_i
                            if tx < term_w:
                                frame_chars[cur_y][tx] = ch
                                frame_colors[cur_y][tx] = key_col

                        for c_i, ch in enumerate(val_str):
                            tx = pane_x + 16 + c_i
                            if tx < term_w:
                                frame_chars[cur_y][tx] = ch
                                frame_colors[cur_y][tx] = val_col

            # Bottom HUD
            hud_y = term_h - 2
            timeline_bar_w = 24
            filled_bars = int((current_time / TOTAL_LOOP_TIME) * timeline_bar_w)
            progress_bar = f"[{'█' * filled_bars}{'░' * (timeline_bar_w - filled_bars)}]"
            pause_tag = " [PAUSED]" if is_paused else ""

            hud_str = f" {progress_bar} {current_time:4.1f}s/30.0s  •  {act_name}{pause_tag}  •  {display_fps} FPS "
            hud_x = max(0, (term_w - len(hud_str)) // 2)

            act_color = (
                rgb_fg(34, 197, 94) if act_idx == 0 else
                rgb_fg(56, 189, 248) if act_idx == 1 else
                rgb_fg(249, 115, 22) if act_idx == 2 else
                rgb_fg(239, 68, 68) if act_idx == 3 else
                rgb_fg(244, 63, 94) if act_idx == 4 else
                rgb_fg(251, 191, 36)
            )

            for i, ch in enumerate(hud_str):
                tx = hud_x + i
                if 0 <= tx < term_w and 0 <= hud_y < term_h:
                    frame_chars[hud_y][tx] = ch
                    frame_colors[hud_y][tx] = act_color

            if is_interactive_boot:
                hotkey_str = "[ENTER / SPACE] Continue to Hartley  •  [Q / ESC] Skip to Prompt  •  [1-6] Acts"
            else:
                hotkey_str = "[SPACE] Blast  •  [F] Inferno  •  [R] Reset  •  [P] Pause  •  [1-6] Acts  •  [Q] Exit"

            hotkey_y = term_h - 1
            hotkey_x = max(0, (term_w - len(hotkey_str)) // 2)
            for i, ch in enumerate(hotkey_str):
                tx = hotkey_x + i
                if 0 <= tx < term_w and 0 <= hotkey_y < term_h:
                    frame_chars[hotkey_y][tx] = ch
                    frame_colors[hotkey_y][tx] = rgb_fg(148, 163, 184) if is_interactive_boot else rgb_fg(100, 116, 139)

            output_buffer = [C_HOME]
            last_col = ""
            for r in range(term_h):
                for c in range(term_w):
                    col = frame_colors[r][c]
                    ch = frame_chars[r][c]
                    if col != last_col:
                        output_buffer.append(col if col else C_RESET)
                        last_col = col
                    output_buffer.append(ch)
                if r < term_h - 1:
                    output_buffer.append("\n")

            sys.stdout.write("".join(output_buffer))
            sys.stdout.flush()

            elapsed = time.time() - now
            time.sleep(max(0.005, 0.033 - elapsed))

    finally:
        if not WINDOWS and orig_settings:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, orig_settings)
            except Exception:
                pass
        cleanup_screen()
