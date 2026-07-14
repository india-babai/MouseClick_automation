# AutoFlow — GUI automation framework (Aladdin → report → ART)

A config-driven mouse/keyboard automation framework for repeating a
manual UI workflow across many customers. Pure `pip install` — no admin
rights, no browser downloads, works on locked-down corporate laptops.

> **Before you run this 700 times:** get written approval from your
> manager/compliance that UI automation of these systems is allowed, and
> ask whether an API route (Aladdin Studio) exists. Also see
> "Better alternatives" at the bottom — try those first.

## Install

```
pip install -r requirements.txt
```

## How it works

- `customers.csv` — one row per customer. Every column becomes a
  `{placeholder}` usable in config text fields.
- `config.json` — the workflow as a list of steps (click, type, wait...).
  Instead of fixed screen coordinates, steps reference **anchor images**:
  small screenshots of buttons/labels that are found on screen at runtime
  (survives window moves, minor layout shifts).
- `anchors/` — the anchor images you capture yourself.
- `state/done.txt` — checkpoint file; completed customers are recorded so
  a crashed/stopped run **resumes exactly where it left off**.
- `state/failures/` — a full-screen screenshot is saved for every failure.
- `state/logs/` — timestamped log per run.

## Setup workflow

1. Open Aladdin and ART, do the flow manually once, and note every
   click/keystroke.
2. Capture anchor images for every button/marker you interact with —
   one session captures them sequentially:
   ```
   python tools/capture_anchor.py
   ```
   For each anchor you get 5 seconds to hover the mouse over the
   element's top-left corner, then 5 seconds for the bottom-right.
   The tool then asks for a name: type one to save it as
   `anchors/<name>.png` and move to the next capture, type `retry`
   to discard and redo the capture, or `quit` when you're done.
3. Edit `config.json` to describe your flow (the shipped one is a
   realistic example — replace it with your real steps and anchors).
4. Validate without touching the mouse:
   ```
   python run.py --dry-run
   ```
5. Pilot with one customer, watching the screen:
   ```
   python run.py --limit 1
   ```
6. Scale up gradually: `--limit 10`, `--limit 50`, then the full run.
   Progress is checkpointed, so run in chunks across days if needed.

**Emergency stop: slam the mouse into the top-left corner of the screen**
(pyautogui failsafe aborts instantly).

## Available actions (config.json)

| action                | keys                                        |
|-----------------------|---------------------------------------------|
| `focus_window`        | `title_contains`                             |
| `click_image`         | `image`, `timeout`, `confidence`, `clicks`, `offset` |
| `click_at`            | `x`, `y` (last resort — avoid)               |
| `wait_for_image`      | `image`, `timeout` — poll until visible      |
| `wait_for_image_gone` | `image`, `timeout` — e.g. wait out a spinner |
| `type_text`           | `text`, `press_enter`                        |
| `paste_text`          | `text`, `press_enter` (clipboard — fast/safe)|
| `clear_field`         | —                                            |
| `hotkey`              | `keys` e.g. `["ctrl","s"]`                   |
| `press`               | `key`, `times`                               |
| `scroll`              | `amount` (+up / −down)                       |
| `wait_seconds`        | `seconds` (avoid — prefer wait_for_image)    |
| `wait_for_file`       | `pattern` (glob), `timeout`, `save_as` — wait for a download to finish |
| `copy_file`           | `src`, `dest`, `save_as`                     |
| `move_file`           | `src`, `dest`, `save_as`                     |
| `check_file_exists`   | `path` — fail fast if a file is missing      |

Any step accepts `note` (shown in logs) and `"optional": true` (if the
anchor never appears, skip the step instead of failing — useful for
popups that only show up sometimes).

Placeholders: `{customer_id}` etc. are filled from the CSV row. A step
with `save_as` stores its resulting file path as a new placeholder for
later steps — e.g. `wait_for_file` with `"save_as": "downloaded_file"`
lets any later step use `{downloaded_file}`.

Rule of thumb: use GUI actions only for things that exist *only* on
screen (buttons inside the web apps). Anything involving files — finding
the downloaded file, renaming, copying, staging — uses the file actions:
pure Python, far more reliable than clicking through Explorer windows.

## Settings (config.json → settings)

- `on_error`: `"stop"` (default, safe) or `"skip"` (log, screenshot, move on)
- `max_retries`: re-attempts per customer before stop/skip
- `confidence`: image-match threshold (lower = more tolerant, riskier)
- `action_delay`: pause between steps

## Hard-won rules for reliable runs

1. **The machine is unusable while it runs.** The script owns the mouse.
   Ask for a spare machine/VM if possible.
2. **Freeze the environment**: same monitor, 100% Windows display scaling
   (or re-capture anchors at your scaling), browser zoom 100%, window
   maximized. Anchor images are resolution-dependent.
3. **Silence popups**: Windows Focus Assist ON, Teams/Outlook notifications
   off — a toast over a button breaks image matching.
4. The script calls `keep_awake()` so the screen won't lock mid-run, but
   corporate GPO forced-lock can override it — test a 30-min run first.
5. **Verify success, don't assume it**: always end the flow with a
   `wait_for_image` on a success marker (e.g. ART's "upload complete"),
   never just click-and-hope.
6. Anchor images should be tight crops with distinctive pixels and no
   changing content (dates, counts, usernames).
7. In Windows file dialogs, **paste the full file path** into the filename
   box instead of browsing folders — far more reliable.
8. Reconcile at the end: count files uploaded in ART vs. lines in
   `state/done.txt`.

## Better alternatives (try before pixel automation)

1. **Replay the HTTP calls.** Open DevTools → Network, generate one report,
   inspect the request. If it's a plain POST, a `requests` loop with your
   session cookies does all 700 unattended in minutes.
2. **Attach Selenium/Playwright to your existing Edge** (no downloads):
   ```
   msedge.exe --remote-debugging-port=9222 --user-data-dir=C:\temp\edgeprof
   ```
   ```python
   from playwright.sync_api import sync_playwright
   p = sync_playwright().start()
   browser = p.chromium.connect_over_cdp("http://localhost:9222")
   page = browser.contexts[0].pages[0]   # your already-logged-in tab
   ```
   DOM-based clicking is vastly more reliable than image matching.
3. **pywinauto (UI Automation API)** for native Windows apps/dialogs —
   element-based, pip-only, no admin.

Use this framework when those are blocked (Citrix/virtual apps, disabled
debug ports, canvas-rendered UIs).
