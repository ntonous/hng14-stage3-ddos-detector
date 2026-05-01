import subprocess
import time

blocked_ips = {}

def block_ip(ip, duration_minutes):
    if ip in blocked_ips:
        return False
    
    try:
        subprocess.run(["/sbin/iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"], 
                      capture_output=True)
        blocked_ips[ip] = time.time() + (duration_minutes * 60)
        print(f"Blocked {ip}")
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False

def unblock_ip(ip):
    if ip in blocked_ips:
        try:
            subprocess.run(["/sbin/iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"])
            del blocked_ips[ip]
            return True
        except:
            pass
    return False
