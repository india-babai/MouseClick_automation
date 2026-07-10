"""
Live mouse-position display. Use to find coordinates or check DPI issues.
Run:  python tools/mouse_position.py    (Ctrl+C to quit)
"""

import time

import pyautogui

print("Move the mouse around. Ctrl+C to quit.")
try:
    while True:
        x, y = pyautogui.position()
        print(f"\rX: {x:5d}  Y: {y:5d}", end="", flush=True)
        time.sleep(0.05)
except KeyboardInterrupt:
    print()
