"""
Flow runner: executes the step list from config.json once per customer,
with checkpointing (resume after crash), retries, and failure screenshots.
"""

import csv
import glob as globmod
import json
import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path

from . import actions

ROOT = Path(__file__).resolve().parent.parent
DONE_FILE = ROOT / "state" / "done.txt"
FAIL_DIR = ROOT / "state" / "failures"
LOG_DIR = ROOT / "state" / "logs"

log = logging.getLogger("autoflow")


def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logfile = LOG_DIR / f"run_{datetime.now():%Y%m%d_%H%M%S}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(logfile, encoding="utf-8"),
                  logging.StreamHandler()],
    )


def load_config(path=None):
    path = Path(path) if path else ROOT / "config.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_customers(path=None, id_column="customer_id"):
    """Read customer list from CSV. Every column becomes a {placeholder}."""
    path = Path(path) if path else ROOT / "customers.csv"
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if rows and id_column not in rows[0]:
        raise KeyError(
            f"CSV must have a '{id_column}' column; found {list(rows[0])}"
        )
    return rows


def load_done():
    if not DONE_FILE.exists():
        return set()
    return set(DONE_FILE.read_text(encoding="utf-8").split())


def mark_done(customer_id: str):
    DONE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DONE_FILE, "a", encoding="utf-8") as f:
        f.write(customer_id + "\n")


def _fill(value, customer: dict):
    """Substitute {column_name} placeholders from the customer row."""
    if isinstance(value, str):
        return value.format(**customer)
    return value


INCOMPLETE_SUFFIXES = (".crdownload", ".partial", ".tmp", ".part")


def wait_for_file(pattern: str, timeout: float = 120,
                  stable_seconds: float = 2.0) -> str:
    """Wait until a file matching the glob pattern exists and its size has
    stopped changing (i.e. the download finished). Returns the newest match.
    Browser in-progress files (.crdownload/.partial/...) are ignored."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        matches = [p for p in globmod.glob(pattern)
                   if not p.lower().endswith(INCOMPLETE_SUFFIXES)]
        if matches:
            newest = max(matches, key=os.path.getmtime)
            size1 = os.path.getsize(newest)
            time.sleep(stable_seconds)
            if os.path.exists(newest) and os.path.getsize(newest) == size1:
                return newest
            continue  # still growing - keep polling
        time.sleep(0.5)
    raise TimeoutError(f"No stable file matching '{pattern}' after {timeout}s")


def run_step(step: dict, customer: dict, settings: dict):
    action = step["action"]
    timeout = step.get("timeout", settings.get("default_timeout", 30))
    confidence = step.get("confidence", settings.get("confidence", 0.85))

    if action == "focus_window":
        actions.focus_window(_fill(step["title_contains"], customer), timeout)
    elif action == "click_image":
        actions.click_image(step["image"], timeout, confidence,
                            clicks=step.get("clicks", 1),
                            offset=tuple(step.get("offset", (0, 0))))
    elif action == "click_at":
        actions.click_at(step["x"], step["y"], clicks=step.get("clicks", 1))
    elif action == "wait_for_image":
        actions.wait_for_image(step["image"], timeout, confidence)
    elif action == "wait_for_image_gone":
        actions.wait_for_image_gone(step["image"], timeout, confidence)
    elif action == "type_text":
        actions.type_text(_fill(step["text"], customer),
                          press_enter=step.get("press_enter", False))
    elif action == "paste_text":
        actions.paste_text(_fill(step["text"], customer),
                           press_enter=step.get("press_enter", False))
    elif action == "clear_field":
        actions.clear_field()
    elif action == "hotkey":
        actions.hotkey(*step["keys"])
    elif action == "press":
        actions.press(step["key"], times=step.get("times", 1))
    elif action == "scroll":
        actions.scroll(step["amount"])
    elif action == "wait_seconds":
        time.sleep(step["seconds"])

    # ---- file-system actions (no GUI involved - never click through
    # Explorer for file work; do it directly in Python) ----
    elif action == "wait_for_file":
        found = wait_for_file(_fill(step["pattern"], customer), timeout,
                              stable_seconds=step.get("stable_seconds", 2.0))
        log.info("    found file: %s", found)
        if step.get("save_as"):
            customer[step["save_as"]] = found
    elif action == "copy_file":
        src = _fill(step["src"], customer)
        dest = _fill(step["dest"], customer)
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        if step.get("save_as"):
            customer[step["save_as"]] = dest
    elif action == "move_file":
        src = _fill(step["src"], customer)
        dest = _fill(step["dest"], customer)
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src, dest)
        if step.get("save_as"):
            customer[step["save_as"]] = dest
    elif action == "check_file_exists":
        path = _fill(step["path"], customer)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Expected file missing: {path}")
    else:
        raise ValueError(f"Unknown action: {action}")


def run_customer(flow, customer: dict, settings: dict):
    delay = settings.get("action_delay", 0.4)
    # copy so save_as variables from one customer never leak into the next
    customer = dict(customer)
    for i, step in enumerate(flow, 1):
        desc = step.get("note", step["action"])
        log.info("  step %d/%d: %s", i, len(flow), desc)
        try:
            run_step(step, customer, settings)
        except actions.AnchorNotFound:
            if step.get("optional"):
                log.info("    optional step - anchor not found, skipping")
                continue
            raise
        time.sleep(delay)


def run(config_path=None, customers_path=None, dry_run=False,
        limit=None, no_resume=False):
    setup_logging()
    cfg = load_config(config_path)
    settings = cfg.get("settings", {})
    flow = cfg["flow"]
    id_col = settings.get("id_column", "customer_id")
    customers = load_customers(customers_path, id_col)

    done = set() if no_resume else load_done()
    todo = [c for c in customers if c[id_col] not in done]
    if limit:
        todo = todo[:limit]

    log.info("Total customers: %d | already done: %d | this run: %d",
             len(customers), len(done), len(todo))

    if dry_run:
        for c in todo[:3]:
            log.info("DRY RUN - would process %s with steps:", c[id_col])
            for step in flow:
                filled = {k: _fill(v, c) if isinstance(v, str) else v
                          for k, v in step.items()}
                log.info("    %s", filled)
        return

    actions.keep_awake()
    max_retries = settings.get("max_retries", 1)
    on_error = settings.get("on_error", "stop")  # "stop" or "skip"
    ok = fail = 0

    for n, customer in enumerate(todo, 1):
        cid = customer[id_col]
        log.info("[%d/%d] customer %s", n, len(todo), cid)
        attempt = 0
        while True:
            try:
                run_customer(flow, customer, settings)
                mark_done(cid)
                ok += 1
                break
            except Exception as e:
                attempt += 1
                shot = FAIL_DIR / f"{cid}_attempt{attempt}.png"
                actions.screenshot(str(shot))
                log.error("customer %s attempt %d failed: %s (screenshot: %s)",
                          cid, attempt, e, shot)
                if attempt <= max_retries:
                    log.info("retrying %s ...", cid)
                    continue
                fail += 1
                if on_error == "skip":
                    log.warning("skipping %s, moving on", cid)
                    break
                log.error("on_error=stop -> halting run. "
                          "Fix the issue and re-run; progress is saved.")
                log.info("SUMMARY: ok=%d failed=%d remaining=%d",
                         ok, fail, len(todo) - n)
                return

    log.info("SUMMARY: ok=%d failed=%d", ok, fail)
