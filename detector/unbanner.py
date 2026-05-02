"""
unbanner.py — Ban schedule tracker.

Tracks per-IP ban count and returns the next ban duration.
Schedule: 10min → 30min → 2hr → permanent (4th+ offense)
"""

import logging

logger = logging.getLogger("unbanner")

# Tracks how many times each IP has been banned
ban_count = {}

# Ban schedule in seconds. -1 = permanent.
BAN_SCHEDULE = [600, 1800, 7200, -1]


def configure(cfg):
    global BAN_SCHEDULE
    schedule = cfg.get("ban_schedule", [600, 1800, 7200, -1])
    BAN_SCHEDULE = schedule


def get_duration(ip):
    """
    Return the next ban duration in seconds for this IP.
    Returns -1 for permanent ban (4th offense and beyond).
    Increments the ban count for next call.
    """
    count = ban_count.get(ip, 0)
    idx = min(count, len(BAN_SCHEDULE) - 1)
    duration = BAN_SCHEDULE[idx]

    ban_count[ip] = count + 1

    if duration == -1:
        logger.info("[UNBANNER] ip=%s offense=%d → PERMANENT", ip, count + 1)
    else:
        logger.info("[UNBANNER] ip=%s offense=%d → %ds", ip, count + 1, duration)

    return duration


def get_ban_count(ip):
    return ban_count.get(ip, 0)


def reset(ip):
    """Reset ban history for an IP (for testing)."""
    ban_count.pop(ip, None)
