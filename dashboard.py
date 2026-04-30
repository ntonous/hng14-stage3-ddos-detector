from flask import Flask
import time

app = Flask(__name__)

START_TIME = time.time()

# shared values updated by main.py if imported
stats = {
    "cpu": 0,
    "ram": 0,
    "disk": 0,
    "global_rate": 0,
    "mean": 1.0,
    "std": 1.0,
    "blocked_count": 0,
    "blocked_ips": [],
    "top_ips": [],
    "audit": []
}


def uptime():
    secs = int(time.time() - START_TIME)
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    return f"{h}h {m}m {s}s"


@app.route("/")
def dashboard():
    rows = ""
    for item in stats["top_ips"][:10]:
        ip = item[0]
        count = item[1]
        rows += f"<tr><td>{ip}</td><td>{count}</td></tr>"

    blocked = "<br>".join(stats["blocked_ips"]) if stats["blocked_ips"] else "None"
    audit_lines = "\n".join(stats["audit"][-10:])

    return f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="3">
        <title>HNG DDOS Detector Dashboard</title>
        <style>
            body {{
                background:#0f172a;
                color:white;
                font-family:Arial;
                padding:30px;
            }}
            .card {{
                background:#1e293b;
                padding:18px;
                margin:10px;
                border-radius:12px;
                display:inline-block;
                width:220px;
                vertical-align:top;
            }}
            table {{
                width:100%;
                border-collapse:collapse;
                margin-top:20px;
            }}
            td, th {{
                border:1px solid #334155;
                padding:8px;
            }}
            h1,h2 {{
                color:#38bdf8;
            }}
        </style>
    </head>
    <body>
        <h1>🚀 HNG DDOS Detector Dashboard</h1>

        <div class="card">CPU Usage<br><b>{stats["cpu"]}%</b></div>
        <div class="card">RAM Usage<br><b>{stats["ram"]}%</b></div>
        <div class="card">Disk Usage<br><b>{stats["disk"]}%</b></div>
        <div class="card">Global Req/s<br><b>{stats["global_rate"]}</b></div>
        <div class="card">Mean<br><b>{stats["mean"]:.2f}</b></div>
        <div class="card">Std Dev<br><b>{stats["std"]:.2f}</b></div>
        <div class="card">Blocked IPs<br><b>{stats["blocked_count"]}</b></div>
        <div class="card">Uptime<br><b>{uptime()}</b></div>

        <h2>Blocked Addresses</h2>
        <div>{blocked}</div>

        <h2>Top 10 Source IPs</h2>
        <table>
            <tr><th>IP</th><th>Requests</th></tr>
            {rows}
        </table>

        <h2>Recent Audit Events</h2>
        <pre>{audit_lines}</pre>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
