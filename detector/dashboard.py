from flask import Flask
import time
import psutil
from blocker import blocked
from baseline import get_baseline

app = Flask(__name__)
start_time = time.time()


@app.route("/")
def dashboard():
    uptime = int(time.time() - start_time)
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    avg, std = get_baseline()

    html = f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="3">
        <title>HNG Metrics Dashboard</title>
        <style>
            body {{
                background:#111;
                color:#0f0;
                font-family:Arial;
                padding:30px;
            }}
            h1 {{color:#fff;}}
            .card {{
                background:#222;
                padding:15px;
                margin:10px 0;
                border-radius:8px;
            }}
        </style>
    </head>
    <body>
        <h1>🚀 HNG Detector Dashboard</h1>

        <div class="card">Uptime: {uptime} sec</div>
        <div class="card">CPU Usage: {cpu}%</div>
        <div class="card">Memory Usage: {mem}%</div>
        <div class="card">Baseline Mean: {avg:.2f}</div>
        <div class="card">Baseline Stddev: {std:.2f}</div>
        <div class="card">Banned IP Count: {len(blocked)}</div>
        <div class="card">Blocked IPs: {list(blocked.keys())}</div>

    </body>
    </html>
    """
    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
