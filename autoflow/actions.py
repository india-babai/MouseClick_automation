"""
Low-level screen actions built on pyautogui.

Design principles:
  - Never click blind coordinates when an image anchor can be used instead.
  - Every wait is a poll-until-visible loop with a timeout, never a fixed sleep.
  - Moving the mouse to the TOP-LEFT corner of the screen aborts the run
    (pyautogui FAILSAFE) - this is your emergency brake.
"""

import ctypes
import time
from pathlib import Path

import pyautogui
import pyperclip

# Windows display-scaling (125%/150% DPI) makes screenshot pixels disagree
# with mouse coordinates unless the process declares itself DPI-aware.
try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

pyautogui.FAILSAFE = True   # slam mouse to top-left corner to abort
pyautogui.PAUSE = 0.3       # small breath after every pyautogui call

# Confidence-based matching (tolerant of small rendering differences)
# requires OpenCV. Fail loudly at startup rather than mid-run.
try:
    import cv2  # noqa: F401
except ImportError:
    raise SystemExit(
        "opencv-python is not installed in THIS Python environment - "
        "image matching cannot work reliably without it.\n"
        "Fix:  python -m pip install opencv-python"
    )

ANCHOR_DIR = Path(__file__).resolve().parent.parent / "anchors"


class AnchorNotFound(RuntimeError):
    pass


def _locate(image_name: str, confidence: float = 0.85, region=None):
    """Return center point of the anchor image on screen, or None."""
    path = ANCHOR_DIR / image_name
    if not path.exists():
        raise FileNotFoundError(f"Anchor image missing: {path}")
    try:
        return pyautogui.locateCenterOnScreen(
            str(path), confidence=confidence, region=region
        )
    except pyautogui.ImageNotFoundException:
        return None


def wait_for_image(image_name: str, timeout: float = 30,
                   confidence: float = 0.85, region=None):
    """Poll until the anchor appears. Returns its center point."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        point = _locate(image_name, confidence, region)
        if point:
            return point
        time.sleep(0.5)
    raise AnchorNotFound(
        f"'{image_name}' not visible after {timeout}s "
        f"(confidence={confidence})"
    )


def wait_for_image_gone(image_name: str, timeout: float = 30,
                        confidence: float = 0.85):
    """Poll until the anchor disappears (e.g. a 'Generating...' spinner)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _locate(image_name, confidence) is None:
            return
        time.sleep(0.5)
    raise AnchorNotFound(f"'{image_name}' still visible after {timeout}s")


def click_image(image_name: str, timeout: float = 30,
                confidence: float = 0.85, clicks: int = 1,
                offset=(0, 0)):
    """Wait for the anchor, then click its center (plus optional offset)."""
    x, y = wait_for_image(image_name, timeout, confidence)
    pyautogui.click(x + offset[0], y + offset[1], clicks=clicks)


def click_at(x: int, y: int, clicks: int = 1):
    """Raw coordinate click - avoid unless there is no stable anchor."""
    pyautogui.click(x, y, clicks=clicks)


def type_text(text: str, press_enter: bool = False, interval: float = 0.03):
    """Type character by character (keyboard events)."""
    pyautogui.write(text, interval=interval)
    if press_enter:
        pyautogui.press("enter")


def paste_text(text: str, press_enter: bool = False):
    """Paste via clipboard - faster and safe for special characters."""
    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "v")
    if press_enter:
        pyautogui.press("enter")


def clear_field():
    """Select-all + delete in the currently focused input."""
    pyautogui.hotkey("ctrl", "a")
    pyautogui.press("delete")


def hotkey(*keys: str):
    pyautogui.hotkey(*keys)


def press(key: str, times: int = 1):
    pyautogui.press(key, presses=times)


def scroll(amount: int):
    """Positive = up, negative = down."""
    pyautogui.scroll(amount)


def focus_window(title_contains: str, timeout: float = 10):
    """Bring the first window whose title contains the text to front."""
    import pygetwindow as gw
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        matches = [w for w in gw.getAllWindows()
                   if title_contains.lower() in w.title.lower()]
        if matches:
            win = matches[0]
            try:
                if win.isMinimized:
                    win.restore()
                win.activate()
            except Exception:
                # activate() sometimes throws even when it works
                pass
            time.sleep(0.5)
            return
        time.sleep(0.5)
    raise AnchorNotFound(f"No window with title containing '{title_contains}'")


def screenshot(save_path: str):
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    pyautogui.screenshot(str(save_path))


def keep_awake():
    """Stop Windows from sleeping / locking while the run is active.
    No admin rights required. Call once at start; effect resets on exit."""
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        )
    except Exception:
        pass
