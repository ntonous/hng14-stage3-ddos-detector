"""
dashboard.py — Live metrics web dashboard.

Refreshes every 3 seconds. Shows:
- Banned IPs, global req/s, top 10 source IPs
- CPU/memory usage, effective mean/stddev, uptime
Served at port 9000 (proxied by Nginx to your subdomain).
"""

import time
import psutil
from flask import Flask
from monitor import get_global_rate, get_top_ips
from baseline import baseline
from blocker import get_blocked_list
import audit

app = Flask(__name__)
START_TIME = time.time()


def _uptime():
    secs = int(time.time() - START_TIME)
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m}m {s}s"


@app.route("/")
def home():
    global_rate = get_global_rate()
    mean = baseline["mean"]
    std = baseline["std"]
    top_ips = get_top_ips()
    banned = get_blocked_list()
    audit_lines = audit.get_recent(15)
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent

    # Top IPs table rows
    ip_rows = "".join(
        f"<tr><td>{ip}</td><td>{count}</td></tr>"
        for ip, count in top_ips
    )

    # Banned IPs rows
    ban_rows = "".join(
        f"<tr><td>{b['ip']}</td><td>{b['condition']}</td><td>{b['duration']}</td><td>{b['ban_count']}</td></tr>"
        for b in banned
    ) or "<tr><td colspan='4'>No active bans</td></tr>"

    # Audit log
    audit_html = "\n".join(audit_lines) or "No audit events yet."

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="3">
    <title>HNG DDoS Detector</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: #0f172a;
            color: #e2e8f0;
            font-family: 'Segoe UI', Arial, sans-serif;
            padding: 24px;
        }}
        h1 {{ color: #38bdf8; margin-bottom: 20px; font-size: 1.6rem; }}
        h2 {{ color: #7dd3fc; margin: 24px 0 10px; font-size: 1.1rem; }}
        .cards {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 20px;
        }}
        .card {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 16px 20px;
            min-width: 160px;
            flex: 1;
        }}
        .card .label {{ font-size: 0.78rem; color: #94a3b8; margin-bottom: 6px; }}
        .card .value {{ font-size: 1.5rem; font-weight: bold; color: #38bdf8; }}
        .card.alert .value {{ color: #f87171; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #1e293b;
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 20px;
        }}
        th {{
            background: #0f2744;
            color: #7dd3fc;
            padding: 10px 14px;
            text-align: left;
            font-size: 0.85rem;
        }}
        td {{
            padding: 9px 14px;
            border-top: 1px solid #334155;
            font-size: 0.88rem;
        }}
        tr:hover td {{ background: #253347; }}
        pre {{
            background: #0f2236;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 14px;
            font-size: 0.78rem;
            color: #94a3b8;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 300px;
            overflow-y: auto;
        }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            background: #1d4ed8;
            color: white;
        }}
        .ts {{ font-size: 0.75rem; color: #64748b; float: right; }}
    </style>
</head>
<body>
    <h1>🛡️ HNG DDoS Detector Dashboard</h1>
    <span class="ts">Auto-refresh every 3s &nbsp;|&nbsp; Uptime: {_uptime()}</span>

    <h2>System Metrics</h2>
    <div class="cards">
        <div class="card">
            <div class="label">Global Req/s</div>
            <div class="value">{global_rate}</div>
        </div>
        <div class="card">
            <div class="label">Baseline Mean</div>
            <div class="value">{mean:.2f}</div>
        </div>
        <div class="card">
            <div class="label">Std Dev</div>
            <div class="value">{std:.2f}</div>
        </div>
        <div class="card {'alert' if len(banned) > 0 else ''}">
            <div class="label">Banned IPs</div>
            <div class="value">{len(banned)}</div>
        </div>
        <div class="card">
            <div class="label">CPU Usage</div>
            <div class="value">{cpu}%</div>
        </div>
        <div class="card">
            <div class="label">RAM Usage</div>
            <div class="value">{ram}%</div>
        </div>
    </div>

    <h2>🚫 Active Bans ({len(banned)})</h2>
    <table>
        <tr><th>IP</th><th>Condition</th><th>Duration</th><th>Offense #</th></tr>
        {ban_rows}
    </table>

    <h2>📊 Top 10 Source IPs</h2>
    <table>
        <tr><th>IP Address</th><th>Requests (last 60s)</th></tr>
        {ip_rows if ip_rows else "<tr><td colspan='2'>No traffic yet</td></tr>"}
    </table>

    <h2>📋 Recent Audit Events</h2>
    <pre>{audit_html}</pre>
</body>
</html>"""


def run_dashboard(cfg=None):
    port = 9000
    if cfg:
        port = cfg.get("dashboard", {}).get("port", 9000)
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
