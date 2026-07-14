"""
Capture anchor images (small screenshots of buttons/labels) for use
in config.json - sequentially, from the terminal.

Run:  python tools/capture_anchor.py

The tool then loops, one anchor per pass:
  1. You get 5 seconds to hover the mouse over the TOP-LEFT corner
     of the element -> position is recorded.
  2. Another 5 seconds to hover over the BOTTOM-RIGHT corner.
  3. The region is screenshotted and you are asked to name it:
       - type a name  -> saved to anchors/<name>.png, next capture starts
       - "retry"      -> discard this capture and redo it
       - "quit"       -> discard this capture and stop (done for now)

Tips: capture tightly around the element, include some distinctive
pixels (icon + text), avoid areas that change (dates, counters).
"""

import time
from pathlib import Path

import pyautogui

ANCHOR_DIR = Path(__file__).resolve().parent.parent / "anchors"
CORNER_SECONDS = 5


def countdown(msg, seconds=CORNER_SECONDS):
    print(msg)
    for i in range(seconds, 0, -1):
        print(f"  {i}...", flush=True)
        time.sleep(1)
    return pyautogui.position()


def capture_region():
    """Record both corners and screenshot the region.
    Returns (image, w, h) or None if the region was too small."""
    x1, y1 = countdown("Hover mouse over the TOP-LEFT of the element:")
    print(f"  recorded ({x1}, {y1})")
    x2, y2 = countdown("Now hover over the BOTTOM-RIGHT of the element:")
    print(f"  recorded ({x2}, {y2})")

    left, top = min(x1, x2), min(y1, y2)
    w, h = abs(x2 - x1), abs(y2 - y1)
    if w < 5 or h < 5:
        print(f"Region too small ({w}x{h}px) - let's try that again.")
        return None
    return pyautogui.screenshot(region=(left, top, w, h)), w, h


def ask_name():
    """Prompt until we get a usable name, 'retry' or 'quit'."""
    while True:
        try:
            name = input('Name this anchor ("retry" = redo, "quit" = done): ')
        except (EOFError, KeyboardInterrupt):
            print()
            return "quit"
        name = name.strip()
        if not name:
            continue
        if name.lower() in ("retry", "quit"):
            return name.lower()
        return name.removesuffix(".png")


def main():
    ANCHOR_DIR.mkdir(exist_ok=True)
    saved = 0
    print("Sequential anchor capture - Ctrl+C or 'quit' to finish.\n")

    while True:
        print(f"=== Capturing anchor #{saved + 1} ===")
        try:
            result = capture_region()
        except KeyboardInterrupt:
            print("\nInterrupted.")
            break
        if result is None:
            continue  # region too small - redo this capture
        img, w, h = result

        name = ask_name()
        if name == "retry":
            print("Discarded - capturing again.\n")
            continue
        if name == "quit":
            print("Last capture discarded.")
            break

        out = ANCHOR_DIR / f"{name}.png"
        if out.exists():
            print(f"  (overwriting existing {out.name})")
        img.save(str(out))
        saved += 1
        print(f"Saved {out}  ({w}x{h}px)")
        print(f'Use in config.json as:  "image": "{name}.png"\n')

    print(f"\nDone - {saved} anchor(s) saved to {ANCHOR_DIR}")


if __name__ == "__main__":
    main()
