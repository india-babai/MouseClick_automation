"""
Hover-test an anchor WITHOUT clicking.

Run:  python tools/test_anchor.py gmail_link

Get the target screen visible first (you have 3 seconds after starting).
The script then:
  1. tries to locate the anchor at decreasing confidence levels,
  2. prints where it matched and at what confidence,
  3. SLOWLY moves the mouse onto the match so you can SEE what it found.

If the mouse ends up somewhere other than your element, the anchor is
false-matching: re-capture it tighter / raise "confidence" in config.json.
"""

import sys
import time
from pathlib import Path

import pyautogui

ANCHOR_DIR = Path(__file__).resolve().parent.parent / "anchors"


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/test_anchor.py <anchor_name>")
        sys.exit(1)
    name = sys.argv[1].removesuffix(".png")
    path = ANCHOR_DIR / f"{name}.png"
    if not path.exists():
        print(f"Anchor not found: {path}")
        sys.exit(1)

    print("Switch to the target screen NOW - searching in 3 seconds...")
    time.sleep(3)

    for conf in (0.95, 0.90, 0.85, 0.80, 0.75, 0.70):
        try:
            box = pyautogui.locateOnScreen(str(path), confidence=conf)
        except pyautogui.ImageNotFoundException:
            box = None
        except Exception as e:
            print(f"confidence={conf}: ERROR - {e}")
            print("(if this mentions OpenCV: pip install opencv-python)")
            sys.exit(1)
        if box:
            cx, cy = box.left + box.width // 2, box.top + box.height // 2
            print(f"MATCH at confidence {conf}: box={box}  center=({cx},{cy})")
            print("Moving mouse there now - WATCH where it lands...")
            pyautogui.moveTo(cx, cy, duration=1.5)
            print("Is the mouse on your element? If not, the anchor is")
            print("matching the wrong thing - re-capture tighter and/or")
            print(f'set "confidence": {min(conf + 0.05, 0.95):.2f} on that step.')
            return
        else:
            print(f"confidence={conf}: no match")

    print("No match at any confidence level.")
    print("Likely causes: display scaling / browser zoom changed since")
    print("capture, element not on the visible screen, or anchor was")
    print("edited/resized after capture. Re-capture and try again.")


if __name__ == "__main__":
    main()
