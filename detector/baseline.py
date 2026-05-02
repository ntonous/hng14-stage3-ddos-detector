"""
baseline.py — Rolling 30-minute baseline with per-hour slot preference.

Tracks per-second request counts in a deque.
Recalculates mean/stddev every 60 seconds.
Prefers current hour's data when it has >= 10 samples.
"""

import time
import math
import threading
import logging
from collections import deque, defaultdict

logger = logging.getLogger("baseline")

# ── Config defaults ───────────────────────────────────────────
WINDOW_SECS = 1800      # 30 minutes
RECALC_SECS = 60        # recalculate every 60s
MIN_SAMPLES = 10
FLOOR_MEAN = 1.0
FLOOR_STD = 0.5

# ── Rolling window of per-second counts ──────────────────────
# Each entry: (timestamp, req_count, error_count)
history = deque()

# Per-hour slots: { hour(0-23) -> [counts] }
hourly = defaultdict(list)

# Current second accumulator
_current_ts = int(time.time())
_current_count = 0
_current_errors = 0

# Cached baseline values
baseline = {
    "mean": FLOOR_MEAN,
    "std": FLOOR_STD,
    "error_mean": FLOOR_MEAN,
}

_lock = threading.Lock()
_last_recalc = 0.0
_audit_fn = None  # injected by main.py


def configure(cfg, audit_fn=None):
    global WINDOW_SECS, RECALC_SECS, MIN_SAMPLES, FLOOR_MEAN, FLOOR_STD, _audit_fn
    WINDOW_SECS = cfg.get("baseline_minutes", 30) * 60
    RECALC_SECS = cfg.get("recalc_interval", 60)
    MIN_SAMPLES = cfg.get("min_samples", 10)
    FLOOR_MEAN = cfg.get("floor_mean", 1.0)
    FLOOR_STD = cfg.get("floor_std", 0.5)
    _audit_fn = audit_fn


def record_request(is_error=False):
    """Call once per incoming request from monitor."""
    global _current_count, _current_errors
    with _lock:
        _current_count += 1
        if is_error:
            _current_errors += 1


def _flush():
    """Flush current-second bucket into history. Call every second."""
    global _current_ts, _current_count, _current_errors

    now = int(time.time())
    if now <= _current_ts:
        return

    with _lock:
        count = _current_count
        errors = _current_errors
        ts = _current_ts
        _current_count = 0
        _current_errors = 0
        _current_ts = now

    # Add to rolling window
    history.append((ts, count, errors))

    # Add to hourly slot
    hour = time.localtime(ts).tm_hour
    hourly[hour].append(count)

    # Evict entries older than WINDOW_SECS
    cutoff = now - WINDOW_SECS
    while history and history[0][0] < cutoff:
        history.popleft()

    # Keep hourly slots to last 2 hours only
    current_hour = time.localtime().tm_hour
    prev_hour = (current_hour - 1) % 24
    for h in list(hourly.keys()):
        if h != current_hour and h != prev_hour:
            del hourly[h]


def _compute():
    """Recalculate baseline. Prefer current hour if enough data."""
    global _last_recalc

    now = time.time()
    if now - _last_recalc < RECALC_SECS:
        return
    _last_recalc = now

    if not history:
        return

    # ── Prefer current hour's slot ────────────────────────────
    current_hour = time.localtime().tm_hour
    hour_data = hourly.get(current_hour, [])

    if len(hour_data) >= MIN_SAMPLES:
        data = hour_data
        source = f"hour-{current_hour}"
    else:
        data = [x[1] for x in history]
        source = "rolling-window"

    if not data:
        return

    mean = sum(data) / len(data)
    variance = sum((x - mean) ** 2 for x in data) / len(data)
    std = math.sqrt(variance) if variance > 0 else FLOOR_STD

    # Error baseline from rolling window
    error_data = [x[2] for x in history]
    error_mean = sum(error_data) / len(error_data) if error_data else FLOOR_MEAN

    baseline["mean"] = max(mean, FLOOR_MEAN)
    baseline["std"] = max(std, FLOOR_STD)
    baseline["error_mean"] = max(error_mean, FLOOR_MEAN)

    logger.info(
        "[BASELINE] source=%s samples=%d effective_mean=%.2f stddev=%.2f error_mean=%.2f",
        source, len(data), baseline["mean"], baseline["std"], baseline["error_mean"],
    )

    if _audit_fn:
        _audit_fn(
            "BASELINE_RECALC", "-",
            f"source={source}",
            baseline["mean"],
            baseline["std"],
            "-",
        )


def loop():
    """Background thread: flush every second, recalc every 60s."""
    while True:
        _flush()
        _compute()
        time.sleep(1)


def zscore(rate):
    mean = baseline["mean"]
    std = baseline["std"]
    if std == 0:
        std = FLOOR_STD
    return (rate - mean) / std
