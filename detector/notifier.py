"""
notifier.py — Slack notifications for ban, unban, and global anomaly events.

All alerts include: condition, current rate, baseline, timestamp, ban duration.
"""

import requests
import datetime
import logging
import os

logger = logging.getLogger("notifier")

WEBHOOK = ""


def configure(cfg):
    global WEBHOOK
    # Prefer environment variable over config file
    WEBHOOK = os.environ.get("SLACK_WEBHOOK", "") or cfg.get("slack_webhook", "")
    if not WEBHOOK or WEBHOOK.startswith("${"):
        logger.warning("Slack webhook not configured — alerts will be skipped.")


def _now():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def _post(text):
    if not WEBHOOK or WEBHOOK.startswith("${"):
        logger.info("[SLACK SKIPPED] %s", text)
        return
    try:
        r = requests.post(
            WEBHOOK,
            json={"text": text},
            timeout=5,
        )
        if r.status_code != 200:
            logger.warning("Slack returned %d: %s", r.status_code, r.text)
    except Exception as e:
        logger.error("Slack post failed: %s", e)


def send_ban(ip, condition, rate, baseline_mean, duration):
    """Send a ban notification."""
    msg = (
        f":rotating_light: *IP BANNED*\n"
        f"*IP:* `{ip}`\n"
        f"*Condition:* {condition}\n"
        f"*Rate:* {rate:.2f} req/s\n"
        f"*Baseline:* {baseline_mean:.2f} req/s\n"
        f"*Duration:* {duration}\n"
        f"*Time:* {_now()}"
    )
    logger.info("[SLACK BAN] %s", ip)
    _post(msg)


def send_unban(ip, duration):
    """Send an unban notification."""
    msg = (
        f":white_check_mark: *IP UNBANNED*\n"
        f"*IP:* `{ip}`\n"
        f"*Previous ban duration:* {duration}\n"
        f"*Time:* {_now()}"
    )
    logger.info("[SLACK UNBAN] %s", ip)
    _post(msg)


def send_global_alert(condition, rate, baseline_mean):
    """Send a global anomaly alert (no block applied)."""
    msg = (
        f":warning: *GLOBAL TRAFFIC ANOMALY*\n"
        f"*Condition:* {condition}\n"
        f"*Global Rate:* {rate:.2f} req/s\n"
        f"*Baseline:* {baseline_mean:.2f} req/s\n"
        f"*Action:* Alert only (no IP block)\n"
        f"*Time:* {_now()}"
    )
    logger.warning("[SLACK GLOBAL] condition=%s rate=%.2f", condition, rate)
    _post(msg)


def send(msg):
    """Generic send — used for simple messages."""
    _post(msg)
