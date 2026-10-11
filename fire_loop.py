#!/usr/bin/env python3
"""
Hartley 30-Second Cinematic Loop Animation.

Standalone runner for the 30-second multi-act thermal and cyber loop animation.
"""

import sys
import os

# Ensure package root is in sys.path
script_dir = os.path.dirname(os.path.realpath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

try:
    from hartley_agent.fire_engine import run_cinematic_animation
except ImportError:
    # If run outside package context
    sys.path.append(os.path.abspath(os.path.join(script_dir, "..")))
    from hartley_agent.fire_engine import run_cinematic_animation


def main():
    # Dedicated full loop runner (does not auto-exit on space/enter, uses full loop controls)
    run_cinematic_animation(max_duration=None, is_interactive_boot=False)


if __name__ == "__main__":
    main()
