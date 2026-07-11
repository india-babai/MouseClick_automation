"""
List every window title currently on screen - exactly what
focus_window's "title_contains" matches against.

Run:  python tools/list_windows.py
"""

import pygetwindow as gw

windows = [w for w in gw.getAllWindows() if w.title.strip()]
untitled = len(gw.getAllWindows()) - len(windows)

print(f"{len(windows)} titled windows (+ {untitled} untitled/hidden):\n")
for w in sorted(windows, key=lambda w: w.title.lower()):
    state = "minimized" if w.isMinimized else ("active" if w.isActive else "")
    print(f"  {'[' + state + ']':<12} {w.title}")
