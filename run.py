"""
Entry point.

Usage:
    python run.py --dry-run          # print what would happen, touch nothing
    python run.py --limit 1          # pilot: run exactly 1 customer
    python run.py --limit 10         # small batch
    python run.py                    # full run (resumes where it left off)
    python run.py --no-resume        # ignore done.txt and start from the top

Emergency stop while running: SLAM THE MOUSE INTO THE TOP-LEFT CORNER.
"""

import argparse

from autoflow.runner import run


def main():
    p = argparse.ArgumentParser(description="GUI automation flow runner")
    p.add_argument("--config", default=None, help="path to config.json")
    p.add_argument("--customers", default=None, help="path to customers.csv")
    p.add_argument("--dry-run", action="store_true",
                   help="print resolved steps for first 3 customers, no clicks")
    p.add_argument("--limit", type=int, default=None,
                   help="process at most N customers this run")
    p.add_argument("--no-resume", action="store_true",
                   help="ignore the done-list and process everyone again")
    args = p.parse_args()

    run(config_path=args.config, customers_path=args.customers,
        dry_run=args.dry_run, limit=args.limit, no_resume=args.no_resume)


if __name__ == "__main__":
    main()
