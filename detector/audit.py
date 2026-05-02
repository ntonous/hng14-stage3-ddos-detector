"""
audit.py — Structured audit log writer.

Format: [timestamp] ACTION ip | condition | rate | baseline | duration
Writes for: BAN, UNBAN, GLOBAL_ANOMALY, BASELINE_RECALC
"""

import datetime
import logging
import os
from pathlib import Path

logger = logging.getLogger("audit")

AUDIT_FILE = "/app/logs/audit.log"


def configure(cfg):
    global AUDIT_FILE
    AUDIT_FILE = cfg.get("audit_log", "/app/logs/audit.log")
    Path(AUDIT_FILE).parent.mkdir(parents=True, exist_ok=True)
    logger.info("Audit log: %s", AUDIT_FILE)


def log(action, ip, condition, rate, baseline_val, duration):
    """
    Write one structured audit entry.

    Format: [2024-01-15 12:34:56] BAN 1.2.3.4 | z-score=4.2 | 45.2 | 8.1 | 10min
    """
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    if isinstance(rate, float):
        rate_str = f"{rate:.2f}"
    else:
        rate_str = str(rate)

    if isinstance(baseline_val, float):
        baseline_str = f"{baseline_val:.2f}"
    else:
        baseline_str = str(baseline_val)

    line = f"[{ts}] {action} {ip} | {condition} | {rate_str} | {baseline_str} | {duration}\n"

    try:
        with open(AUDIT_FILE, "a") as f:
            f.write(line)
    except Exception as e:
        logger.error("Failed to write audit log: %s", e)

    logger.info("[AUDIT] %s", line.strip())


def get_recent(n=20):
    """Return last N lines of audit log for dashboard display."""
    try:
        with open(AUDIT_FILE, "r") as f:
            lines = f.readlines()
        return [l.strip() for l in lines[-n:]]
    except FileNotFoundError:
        return []
