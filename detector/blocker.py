"""
blocker.py — IP blocking via iptables with backoff ban schedule.

Ban schedule: 10min → 30min → 2hr → permanent
Sends Slack + audit log on every ban and unban.
"""

import subprocess
import time
import logging

logger = logging.getLogger("blocker")

# { ip -> {"expiry": float|-1, "ban_count": int, "condition": str, "rate": float, "baseline": float, "duration": str} }
blocked = {}

# Injected by main.py
_notifier = None
_audit_fn = None

# Backoff schedule in seconds: 10min, 30min, 2hr, permanent(-1)
BAN_SCHEDULE = [600, 1800, 7200, -1]


def configure(notifier, audit_fn, schedule=None):
    global _notifier, _audit_fn, BAN_SCHEDULE
    _notifier = notifier
    _audit_fn = audit_fn
    if schedule:
        BAN_SCHEDULE = schedule


def _iptables(args):
    """Run iptables command. Returns True on success."""
    try:
        r = subprocess.run(
            ["iptables"] + args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=5,
        )
        if r.returncode != 0:
            logger.warning("iptables error: %s", r.stderr.decode().strip())
            return False
        return True
    except Exception as e:
        logger.error("iptables exception: %s", e)
        return False


def block_ip(ip, condition, rate, baseline_mean):
    """
    Block an IP using iptables. Applies backoff schedule.
    Returns True if block was applied.
    Must be called within 10 seconds of detection.
    """
    # Already permanently banned
    rec = blocked.get(ip)
    if rec:
        if rec["expiry"] == -1:
            logger.info("IP %s already permanently banned.", ip)
            return False
        # Still actively banned
        if rec["expiry"] > time.time():
            logger.info("IP %s still banned, skipping re-ban.", ip)
            return False

    ban_count = blocked[ip]["ban_count"] if ip in blocked else 0
    idx = min(ban_count, len(BAN_SCHEDULE) - 1)
    duration_secs = BAN_SCHEDULE[idx]

    if duration_secs == -1:
        expiry = -1
        duration_str = "permanent"
    else:
        expiry = time.time() + duration_secs
        duration_str = f"{duration_secs // 60}min"

    # ── ADD iptables DROP rule ────────────────────────────────
    ok = _iptables(["-I", "INPUT", "1", "-s", ip, "-j", "DROP"])
    if not ok:
        logger.error("Failed to add iptables rule for %s", ip)
        return False

    blocked[ip] = {
        "expiry": expiry,
        "ban_count": ban_count + 1,
        "condition": condition,
        "rate": rate,
        "baseline": baseline_mean,
        "duration": duration_str,
        "banned_at": time.time(),
    }

    logger.warning(
        "[BAN] ip=%s condition=%s rate=%.2f baseline=%.2f duration=%s",
        ip, condition, rate, baseline_mean, duration_str,
    )

    if _audit_fn:
        _audit_fn("BAN", ip, condition, rate, baseline_mean, duration_str)
    if _notifier:
        _notifier.send_ban(ip, condition, rate, baseline_mean, duration_str)

    return True


def unblock_expired():
    """
    Remove expired bans. Call this every second from main loop.
    Returns list of unbanned IPs.
    """
    now = time.time()
    unbanned = []

    for ip in list(blocked.keys()):
        rec = blocked[ip]
        expiry = rec["expiry"]

        if expiry == -1:
            continue  # permanent

        if now >= expiry:
            ok = _iptables(["-D", "INPUT", "-s", ip, "-j", "DROP"])
            if ok:
                logger.info("[UNBAN] ip=%s", ip)
                if _audit_fn:
                    _audit_fn("UNBAN", ip, rec["condition"], rec["rate"], rec["baseline"], rec["duration"])
                if _notifier:
                    _notifier.send_unban(ip, rec["duration"])
                unbanned.append(ip)
                # Keep record for ban_count history but clear active state
                blocked[ip]["expiry"] = None
                blocked[ip]["banned_at"] = None

    return unbanned


def is_blocked(ip):
    rec = blocked.get(ip)
    if not rec:
        return False
    expiry = rec["expiry"]
    return expiry == -1 or (expiry and time.time() < expiry)


def get_blocked_list():
    """Return list of currently active bans for dashboard."""
    now = time.time()
    result = []
    for ip, rec in blocked.items():
        expiry = rec.get("expiry")
        if expiry == -1 or (expiry and now < expiry):
            result.append({
                "ip": ip,
                "duration": rec.get("duration", "?"),
                "ban_count": rec.get("ban_count", 1),
                "condition": rec.get("condition", "?"),
            })
    return result
