"""
main.py — HNG DDoS Detection Daemon orchestrator.

Wires: monitor → baseline → detector → blocker → notifier → audit → dashboard
Runs continuously as a daemon. NOT a cron job or one-shot script.
"""

import threading
import logging
import sys
import os
import yaml
from pathlib import Path

# ── Configure logging first ───────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("main")

# ── Load config ───────────────────────────────────────────────
def load_config():
    path = Path(os.environ.get("CONFIG_PATH", "/app/config.yaml"))
    with open(path) as f:
        cfg = yaml.safe_load(f)

    # Flatten nested config keys for backward compat
    if "baseline" in cfg:
        b = cfg.pop("baseline")
        cfg.setdefault("baseline_minutes", b.get("window_minutes", 30))
        cfg.setdefault("recalc_interval", b.get("recalc_interval", 60))
        cfg.setdefault("min_samples", b.get("min_samples", 10))
        cfg.setdefault("floor_mean", b.get("floor_mean", 1.0))
        cfg.setdefault("floor_std", b.get("floor_std", 0.5))

    if "detection" in cfg:
        d = cfg.pop("detection")
        cfg.setdefault("zscore_threshold", d.get("zscore_threshold", 3.0))
        cfg.setdefault("multiplier_threshold", d.get("multiplier_threshold", 5.0))

    if "error_detection" in cfg:
        e = cfg.pop("error_detection")
        cfg.setdefault("error_multiplier_threshold", e.get("multiplier", 3.0))

    if "blocking" in cfg:
        bl = cfg.pop("blocking")
        schedule_secs = bl.get("backoff_schedule", [600, 1800, 7200, -1])
        cfg.setdefault("ban_schedule", schedule_secs)

    if "slack" in cfg:
        s = cfg.pop("slack")
        cfg.setdefault("slack_webhook", s.get("slack_webhook", ""))

    # Override webhook from environment
    env_hook = os.environ.get("SLACK_WEBHOOK", "")
    if env_hook:
        cfg["slack_webhook"] = env_hook

    return cfg


# ── Import modules ────────────────────────────────────────────
import baseline as baseline_mod
import detector as detector_mod
import blocker as blocker_mod
import notifier as notifier_mod
import audit as audit_mod
import unbanner as unbanner_mod
from monitor import tail_log, add_request, get_global_rate, get_ip_rate, get_error_rate, get_ip_error_rate
from dashboard import run_dashboard


def main():
    cfg = load_config()

    logger.info("=" * 60)
    logger.info("HNG DDoS Detector starting...")
    logger.info("Log file : %s", cfg.get("log_file"))
    logger.info("Window   : %ds", cfg.get("window_seconds", 60))
    logger.info("Baseline : %dmin rolling", cfg.get("baseline_minutes", 30))
    logger.info("=" * 60)

    # Ensure log dir
    Path(cfg.get("audit_log", "/app/logs/audit.log")).parent.mkdir(parents=True, exist_ok=True)

    # ── Configure all modules ─────────────────────────────────
    audit_mod.configure(cfg)
    baseline_mod.configure(cfg, audit_fn=audit_mod.log)
    detector_mod.configure(cfg)
    notifier_mod.configure(cfg)
    unbanner_mod.configure(cfg)
    blocker_mod.configure(
        notifier=notifier_mod,
        audit_fn=audit_mod.log,
        schedule=cfg.get("ban_schedule", [600, 1800, 7200, -1]),
    )

    # ── Start background threads ──────────────────────────────
    threading.Thread(target=baseline_mod.loop, daemon=True, name="baseline").start()
    threading.Thread(target=run_dashboard, args=(cfg,), daemon=True, name="dashboard").start()

    logger.info("System started. Dashboard running on port %d",
                cfg.get("dashboard", {}).get("port", 9000) if isinstance(cfg.get("dashboard"), dict) else 9000)

    # ── MAIN DETECTION LOOP ───────────────────────────────────
    # tail_log() is a generator — yields (ip, status) for every request
    for ip, status in tail_log(cfg.get("log_file", "/var/log/nginx/hng-access.log")):
        is_error = status >= 400

        # Feed the sliding windows
        add_request(ip, status)

        # Feed the baseline per-second counter
        baseline_mod.record_request(is_error=is_error)

        # ── Unban expired IPs ─────────────────────────────────
        blocker_mod.unblock_expired()

        # Skip detection for already-blocked IPs
        if blocker_mod.is_blocked(ip):
            continue

        mean = baseline_mod.baseline["mean"]
        std = baseline_mod.baseline["std"]
        error_baseline = baseline_mod.baseline["error_mean"]

        ip_rate = get_ip_rate(ip)
        ip_error_rate = get_ip_error_rate(ip)
        global_rate = get_global_rate()
        error_rate = get_error_rate()

        # ── Per-IP anomaly detection ──────────────────────────
        bad_ip, reason = detector_mod.detect_ip(
            ip_rate, mean, std, ip_error_rate, error_baseline
        )

        if bad_ip:
            duration_secs = unbanner_mod.get_duration(ip)
            if duration_secs == -1:
                duration_str = "permanent"
            else:
                duration_str = f"{duration_secs // 60}min"

            logger.warning("[ANOMALY] ip=%s reason=%s rate=%d mean=%.2f", ip, reason, ip_rate, mean)
            blocker_mod.block_ip(ip, reason, ip_rate, mean)

        # ── Global anomaly detection (Slack only, no block) ───
        bad_global, g_reason = detector_mod.detect_global(global_rate, mean, std)

        if bad_global:
            logger.warning("[GLOBAL ANOMALY] reason=%s rate=%d mean=%.2f", g_reason, global_rate, mean)
            notifier_mod.send_global_alert(g_reason, global_rate, mean)
            audit_mod.log("GLOBAL_ANOMALY", "-", g_reason, global_rate, mean, "-")


if __name__ == "__main__":
    main()
