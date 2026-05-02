"""
monitor.py — Tail and parse Nginx JSON access log.

Maintains two deque-based sliding windows (60s):
  - global_window: all requests
  - ip_windows: per-IP requests
  - error_window: all 4xx/5xx requests
  - ip_error_windows: per-IP 4xx/5xx

No rate-limiting libraries used.
"""

import json
import time
import logging
from collections import deque, defaultdict
from pathlib import Path

logger = logging.getLogger("monitor")

WINDOW = 60  # seconds

# ── Sliding windows (deque-based) ─────────────────────────────
global_window = deque()           # timestamps of all requests
ip_windows = defaultdict(deque)   # ip -> timestamps
error_window = deque()            # timestamps of error requests
ip_error_windows = defaultdict(deque)  # ip -> error timestamps
ip_totals = defaultdict(int)      # ip -> all-time count


def _evict(now):
    """Remove entries older than WINDOW seconds from all deques."""
    cutoff = now - WINDOW

    while global_window and global_window[0] < cutoff:
        global_window.popleft()

    while error_window and error_window[0] < cutoff:
        error_window.popleft()

    for ip in list(ip_windows.keys()):
        dq = ip_windows[ip]
        while dq and dq[0] < cutoff:
            dq.popleft()
        if not dq:
            del ip_windows[ip]

    for ip in list(ip_error_windows.keys()):
        dq = ip_error_windows[ip]
        while dq and dq[0] < cutoff:
            dq.popleft()
        if not dq:
            del ip_error_windows[ip]


def add_request(ip, status):
    """Add one request to all sliding windows."""
    now = time.time()
    is_error = status >= 400

    global_window.append(now)
    ip_windows[ip].append(now)
    ip_totals[ip] += 1

    if is_error:
        error_window.append(now)
        ip_error_windows[ip].append(now)

    _evict(now)


def get_global_rate():
    """Requests in last 60s (raw count, not per-second)."""
    return len(global_window)


def get_ip_rate(ip):
    """Requests from this IP in last 60s."""
    return len(ip_windows.get(ip, []))


def get_error_rate():
    """Error requests in last 60s."""
    return len(error_window)


def get_ip_error_rate(ip):
    """Error requests from this IP in last 60s."""
    return len(ip_error_windows.get(ip, []))


def get_top_ips(n=10):
    """Return top N IPs by request count in last 60s."""
    return sorted(
        [(ip, len(dq)) for ip, dq in ip_windows.items()],
        key=lambda x: x[1],
        reverse=True,
    )[:n]


def tail_log(log_path="/var/log/nginx/hng-access.log"):
    """
    Generator: continuously tail the Nginx JSON log.
    Yields (ip, status) for every valid log line.
    Handles log rotation by detecting inode/size changes.
    """
    path = Path(log_path)

    # Wait for log file to appear (useful at startup)
    while not path.exists():
        logger.warning("Waiting for log file: %s", log_path)
        time.sleep(2)

    logger.info("Tailing: %s", log_path)
    current_inode = path.stat().st_ino
    lines_parsed = 0

    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        fh.seek(0, 2)  # seek to end — skip historical lines

        while True:
            line = fh.readline()

            if line:
                parsed = _parse(line)
                if parsed:
                    lines_parsed += 1
                    if lines_parsed % 500 == 0:
                        logger.debug("Parsed %d lines", lines_parsed)
                    yield parsed
            else:
                # No new data — check for log rotation
                try:
                    new_inode = path.stat().st_ino
                    new_size = path.stat().st_size
                    if new_inode != current_inode or new_size < fh.tell():
                        logger.info("Log rotation detected — reopening.")
                        fh.close()
                        fh = open(path, "r", encoding="utf-8", errors="replace")
                        current_inode = new_inode
                except FileNotFoundError:
                    logger.warning("Log file disappeared, waiting...")
                    time.sleep(2)

                time.sleep(0.05)


def _parse(line):
    """
    Parse one JSON log line.
    Returns (ip, status) or None if malformed.
    """
    line = line.strip()
    if not line:
        return None
    try:
        data = json.loads(line)
        raw_ip = data.get("source_ip") or data.get("remote_addr", "unknown")
        ip = raw_ip.split(",")[0].strip() or "unknown"
        status = int(data.get("status", 200))
        return ip, status
    except Exception:
        return None
