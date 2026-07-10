"""
Capture an anchor image (a small screenshot of a button/label) for use
in config.json.

Run:  python tools/capture_anchor.py generate_report_button

Then:
  1. You get 3 seconds to hover the mouse over the TOP-LEFT corner
     of the element -> position is recorded.
  2. Another 3 seconds to hover over the BOTTOM-RIGHT corner.
  3. The cropped screenshot is saved to anchors/<name>.png.

Tips: capture tightly around the element, include some distinctive
pixels (icon + text), avoid areas that change (dates, counters).
"""

import sys
import time
from pathlib import Path

import pyautogui

ANCHOR_DIR = Path(__file__).resolve().parent.parent / "anchors"


def countdown(msg, seconds=3):
    print(msg)
    for i in range(seconds, 0, -1):
        print(f"  {i}...", flush=True)
        time.sleep(1)
    return pyautogui.position()


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/capture_anchor.py <anchor_name>")
        sys.exit(1)
    name = sys.argv[1].removesuffix(".png")

    x1, y1 = countdown("Hover mouse over the TOP-LEFT of the element:")
    print(f"  recorded ({x1}, {y1})")
    x2, y2 = countdown("Now hover over the BOTTOM-RIGHT of the element:")
    print(f"  recorded ({x2}, {y2})")

    left, top = min(x1, x2), min(y1, y2)
    w, h = abs(x2 - x1), abs(y2 - y1)
    if w < 5 or h < 5:
        print("Region too small - try again.")
        sys.exit(1)

    ANCHOR_DIR.mkdir(exist_ok=True)
    out = ANCHOR_DIR / f"{name}.png"
    pyautogui.screenshot(str(out), region=(left, top, w, h))
    print(f"Saved {out}  ({w}x{h}px)")
    print(f'Use in config.json as:  "image": "{name}.png"')


if __name__ == "__main__":
    main()
