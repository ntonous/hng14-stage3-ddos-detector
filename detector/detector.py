"""
detector.py — Anomaly detection logic.

Checks z-score AND rate multiplier thresholds.
Automatically tightens thresholds when an IP has an error surge.
"""

import logging

logger = logging.getLogger("detector")

# ── Defaults (loaded from config) ────────────────────────────
Z_THRESHOLD = 3.0
MULTIPLIER = 5.0
ERROR_MULTIPLIER = 3.0
TIGHTENED_Z = 2.0
TIGHTENED_MULT = 3.0


def configure(cfg):
    global Z_THRESHOLD, MULTIPLIER, ERROR_MULTIPLIER, TIGHTENED_Z, TIGHTENED_MULT
    Z_THRESHOLD = cfg.get("zscore_threshold", 3.0)
    MULTIPLIER = cfg.get("multiplier_threshold", 5.0)
    ERROR_MULTIPLIER = cfg.get("error_multiplier_threshold", 3.0)
    TIGHTENED_Z = cfg.get("tightened_zscore", 2.0)
    TIGHTENED_MULT = cfg.get("tightened_multiplier", 3.0)


def detect_ip(ip_rate, mean, std, ip_error_rate=0, baseline_error=0):
    """
    Check if per-IP rate is anomalous.
    Tightens thresholds if IP has an error surge (4xx/5xx > 3x baseline error rate).
    Returns (is_anomalous, condition_string).
    """
    if std == 0:
        std = 0.5

    # ── Error surge check → tighten thresholds ───────────────
    error_surge = baseline_error > 0 and ip_error_rate > ERROR_MULTIPLIER * baseline_error
    z_limit = TIGHTENED_Z if error_surge else Z_THRESHOLD
    mult = TIGHTENED_MULT if error_surge else MULTIPLIER
    suffix = " [error-surge]" if error_surge else ""

    z = (ip_rate - mean) / std

    # Z-score fires first
    if z > z_limit:
        return True, f"z-score={z:.2f}>{z_limit}{suffix}"

    # Rate multiplier check
    if mean > 0 and ip_rate > mean * mult:
        return True, f"{ip_rate:.1f}req/s>{mult}x baseline{suffix}"

    return False, None


def detect_global(global_rate, mean, std):
    """
    Check if global rate is anomalous.
    Global anomaly → Slack alert only, no IP block.
    Returns (is_anomalous, condition_string).
    """
    if std == 0:
        std = 0.5

    z = (global_rate - mean) / std

    if z > Z_THRESHOLD:
        return True, f"global z-score={z:.2f}>{Z_THRESHOLD}"

    if mean > 0 and global_rate > mean * MULTIPLIER:
        return True, f"global {global_rate:.1f}req/s>{MULTIPLIER}x baseline"

    return False, None


def detect_error_surge(ip_error_rate, baseline_error):
    """Returns True if IP error rate is > 3x the baseline error rate."""
    if baseline_error <= 0:
        return False
    return ip_error_rate > ERROR_MULTIPLIER * baseline_error
