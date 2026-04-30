import subprocess
import time


def process_unbans(blocked):
    now = time.time()

    expired = []

    for ip, expiry in blocked.items():
        if now >= expiry:
            subprocess.run(
                ["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            print(f"[UNBAN] Released IP: {ip}")

            expired.append(ip)

    for ip in expired:
        del blocked[ip]
