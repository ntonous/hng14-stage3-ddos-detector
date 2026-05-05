# 🛡️ HNG Stage 3 — DDoS Anomaly Detection Engine

A real-time HTTP traffic anomaly detection daemon built alongside Nextcloud. It watches Nginx access logs, learns what normal traffic looks like, and automatically blocks suspicious IPs using iptables — all without any rate-limiting libraries.

---

## 🌐 Live Links

| Resource | URL |
|----------|-----|
| **Metrics Dashboard** | http://metrics.ntscomputers.dpdns.org |
| **Server IP** | 52.233.247.107 |
| **Nextcloud** | http://52.233.247.107 (IP only) |
| **GitHub Repo** | https://github.com/ntonous/hng14-stage3-ddos-detector |

---

## 📖 Language Choice

**Python** — chosen because:
- Built-in `collections.deque` is perfect for sliding window implementation
- `statistics` module provides mean/stddev without external dependencies
- `subprocess` makes iptables calls straightforward
- Flask gives a lightweight dashboard with zero configuration
- Easier to read and audit detection logic (important for security tools)

---

## 🪟 How the Sliding Window Works

Two deque-based windows track request rates over the last **60 seconds**:

```
global_window = deque()         # all requests
ip_windows    = defaultdict(deque)  # per-IP requests
```

**Eviction logic:** Every time a new request arrives, we call `_evict(now)`:

```python
cutoff = now - 60  # 60 seconds ago

# Remove entries older than cutoff from the LEFT of each deque
while global_window and global_window[0] < cutoff:
    global_window.popleft()
```

Because timestamps are always appended to the RIGHT in arrival order, old entries always accumulate on the LEFT — making eviction O(1) per entry. The deque never grows beyond 60 seconds of data.

**Rate calculation:**
```python
global_rate = len(global_window)      # requests in last 60s
ip_rate     = len(ip_windows[ip])     # requests from this IP in last 60s
```

No counters, no per-minute buckets — every entry is a real timestamp.

---

## 📊 How the Baseline Works

The rolling baseline tracks **per-second request counts** over the last **30 minutes**:

```
history = deque()   # entries: (timestamp, req_count, error_count)
hourly  = defaultdict(list)   # per-hour slots: { hour -> [counts] }
```

**Window size:** 1800 seconds (30 minutes). Entries older than this are evicted from the left of the deque.

**Recalculation interval:** Every **60 seconds**, `_compute()` runs:

```python
# Prefer current hour's data if it has enough samples
hour_data = hourly.get(current_hour, [])
if len(hour_data) >= 10:
    data = hour_data        # use hour slot (more relevant)
else:
    data = rolling_window   # fall back to full 30-min window

mean = sum(data) / len(data)
std  = sqrt(sum((x - mean)**2 for x in data) / len(data))
```

**Floor values** prevent division-by-zero and false positives at startup:
```yaml
floor_mean:   1.0   # effective_mean never goes below this
floor_std:    0.5   # effective_stddev never goes below this
```

**Per-hour slots** allow the baseline to adapt to traffic patterns — busy hours (morning) get a higher mean than quiet hours (night), so the detector doesn't false-positive during normal peak traffic.

---

## 🚨 How Detection Works

Every second, for each active IP and globally:

```
z-score = (current_rate - baseline_mean) / baseline_stddev
```

An anomaly is flagged if **either** condition fires first:
1. `z-score > 3.0` — statistically unusual (3 standard deviations above normal)
2. `rate > 5x baseline_mean` — raw multiplier check

**Error surge tightening:** If an IP's 4xx/5xx rate exceeds `3x` the baseline error rate, thresholds tighten automatically:
- Z-score threshold: `3.0 → 2.0`
- Rate multiplier: `5x → 3x`

**Global vs per-IP:**
- Per-IP anomaly → iptables DROP + Slack alert
- Global anomaly → Slack alert only (no single IP to block)

---

## 🔧 Setup — Fresh VPS to Fully Running Stack

### Prerequisites
- Ubuntu 20.04+ VPS (min 2 vCPU, 2GB RAM)
- Docker + Docker Compose installed
- Domain pointing to your server IP

### Step 1 — Install Docker
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

### Step 2 — Clone the repo
```bash
git clone https://github.com/ntonous/hng14-stage3-ddos-detector.git
cd hng14-stage3-ddos-detector
```

### Step 3 — Set your Slack webhook
```bash
echo 'SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL' > .env
export SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Step 4 — Deploy
```bash
chmod +x deploy.sh
./deploy.sh
```

### Step 5 — Set up dashboard subdomain (optional)
```bash
sudo apt install nginx -y
sudo tee /etc/nginx/sites-available/dashboard << 'EOF'
server {
    listen 80;
    server_name metrics.yourdomain.com;
    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF
sudo ln -sf /etc/nginx/sites-available/dashboard /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### Step 6 — Verify everything is running
```bash
docker ps                          # all 3 containers should show "Up"
docker logs hng-detector -f        # watch live detection logs
curl http://localhost:9000          # test dashboard
```

---

## 📁 Repository Structure

```
hng14-stage3-ddos-detector/
├── detector/
│   ├── main.py          # Orchestrator — wires all modules together
│   ├── monitor.py       # Log tailer + sliding window deques
│   ├── baseline.py      # Rolling 30-min baseline + per-hour slots
│   ├── detector.py      # Z-score + multiplier anomaly detection
│   ├── blocker.py       # iptables blocking + backoff schedule
│   ├── unbanner.py      # Ban duration tracker (10m→30m→2h→permanent)
│   ├── notifier.py      # Slack alerts for ban/unban/global events
│   ├── dashboard.py     # Flask live metrics UI (port 9000)
│   ├── audit.py         # Structured audit log writer
│   ├── config.yaml      # All thresholds (no hardcoded values)
│   ├── requirements.txt
│   └── Dockerfile
├── nginx/
│   └── nginx.conf       # Reverse proxy + JSON access logs
├── docs/
│   └── architecture.png
├── screenshots/
├── docker-compose.yml
├── deploy.sh
└── README.md
```

---

## 📸 Required Screenshots

| Screenshot | Description |
|------------|-------------|
| `Tool-running.png` | Daemon running, processing log lines |
| `Ban-slack.png` | Slack ban notification |
| `Unban-slack.png` | Slack unban notification |
| `Global-alert-slack.png` | Slack global anomaly notification |
| `Iptables-banned.png` | `sudo iptables -L -n` showing blocked IP |
| `Audit-log.png` | Structured log with ban/unban/baseline events |
| `Baseline-graph.png` | Baseline over time — two hourly slots with different means |

---

## 📝 Blog Post

Read the full beginner-friendly breakdown of how this was built:

👉 **[How I Built a Real-Time DDoS Detection Engine from Scratch]https://dev.to/hezekiah_umoh/how-i-built-a-real-time-ddos-detection-engine-from-scratch-11ei**

---

## ⚙️ Configuration Reference

All thresholds live in `detector/config.yaml`:

```yaml
zscore_threshold: 3.0          # flag if z-score exceeds this
multiplier_threshold: 5.0      # flag if rate > N * baseline mean
error_multiplier_threshold: 3.0 # tighten thresholds on error surge
tightened_zscore: 2.0          # tightened z-score during error surge
tightened_multiplier: 3.0      # tightened multiplier during error surge
ban_schedule: [600, 1800, 7200, -1]  # 10min → 30min → 2hr → permanent
floor_mean: 1.0                # minimum baseline mean
floor_std: 0.5                 # minimum baseline stddev
```

---

## 🚫 What This Does NOT Use

- ❌ Fail2Ban
- ❌ Rate-limiting libraries (slowapi, etc.)
- ❌ Per-minute counters
- ❌ Hardcoded effective_mean
