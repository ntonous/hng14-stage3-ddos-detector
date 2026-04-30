import subprocess
import time

blocked = {}

def block_ip(ip, minutes=10):
    if ip in blocked:
        return False

    subprocess.run(
        ["sudo", "iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    blocked[ip] = time.time() + (minutes * 60)
    return True


def unblock_expired():
    now = time.time()
    expired = []

    for ip, expiry in blocked.items():
        if now >= expiry:
            subprocess.run(
                ["sudo", "iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            expired.append(ip)

    for ip in expired:
        del blocked[ip]
