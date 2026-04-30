import yaml
import time
from collections import defaultdict, deque
from datetime import datetime

from monitor import follow
from baseline import add_sample, get_baseline, zscore
from blocker import block_ip, blocked
from unbanner import process_unbans
from detector import ip_anomaly, global_anomaly

# load config
with open("config.yaml") as f:
    config = yaml.safe_load(f)

LOG_FILE = config["log_file"]
WINDOW = config["window_seconds"]
MULTIPLIER = config["multiplier_threshold"]
ZSCORE_LIMIT = config["zscore_threshold"]
BAN_MINUTES = config["ban_minutes"]
AUDIT_LOG = config["audit_log"]

per_ip = defaultdict(deque)
global_window = deque()

last_recalc = time.time()


def audit(action, ip, condition, rate, baseline, duration):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    line = f"[{ts}] {action} {ip} | {condition} | {rate} | {baseline} | {duration}\n"

    with open(AUDIT_LOG, "a") as f:
        f.write(line)


print("Detector Started...")


for entry in follow(LOG_FILE):

    now = time.time()

    # unban expired IPs
    process_unbans(blocked)

    ip = entry.get("source_ip", "").strip()

    if not ip:
        continue

    # PER IP WINDOW
    per_ip[ip].append(now)

    while per_ip[ip] and now - per_ip[ip][0] > WINDOW:
        per_ip[ip].popleft()

    ip_rate = len(per_ip[ip])

    # GLOBAL WINDOW
    global_window.append(now)

    while global_window and now - global_window[0] > WINDOW:
        global_window.popleft()

    global_rate = len(global_window)

    # RECALCULATE BASELINE every 60 sec
    if now - last_recalc >= 60:
        add_sample(global_rate)

        avg, std = get_baseline()

        audit(
            "BASELINE",
            "-",
            "recalc",
            global_rate,
            f"{avg:.2f}/{std:.2f}",
            "-"
        )

        last_recalc = now

    avg, std = get_baseline()

    ip_z = zscore(ip_rate)
    global_z = zscore(global_rate)

    # PER IP DETECTION
    bad_ip, reason = ip_anomaly(
        ip_rate,
        avg,
        ip_z,
        ZSCORE_LIMIT,
        MULTIPLIER
    )

    if bad_ip:
        if block_ip(ip, BAN_MINUTES):
            print(f"[ALERT] Blocked IP: {ip}")

            audit(
                "BAN",
                ip,
                reason,
                ip_rate,
                f"{avg:.2f}",
                f"{BAN_MINUTES}m"
            )

    # GLOBAL DETECTION
    bad_global, greason = global_anomaly(
        global_rate,
        avg,
        global_z,
        ZSCORE_LIMIT,
        MULTIPLIER
    )

    if bad_global:
        print("[GLOBAL ALERT] Traffic spike detected")

        audit(
            "GLOBAL",
            "-",
            greason,
            global_rate,
            f"{avg:.2f}",
            "-"
        )

    print(
        f"{ip} | ip_rate={ip_rate} | global={global_rate}"
    )
