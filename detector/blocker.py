import subprocess
import time

blocked = {}


def block_ip(ip, minutes=10):
    if ip in blocked:
        return False

    subprocess.run(
        ["iptables", "-I", "INPUT", "-s", ip, "-j", "DROP"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    blocked[ip] = time.time() + (minutes * 60)

    return True
