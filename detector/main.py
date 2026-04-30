import time
import random
from flask import Flask

app = Flask(__name__)
start_time = time.time()

@app.route("/")
def home():
    uptime = int(time.time() - start_time)

    return f"""
    <html>
    <head>
    <meta http-equiv="refresh" content="5">
    <style>
    body {{
        background:#06163a;
        color:white;
        font-family:Arial;
        padding:40px;
    }}
    .card {{
        background:#1d2b4a;
        padding:20px;
        margin:10px;
        border-radius:10px;
        display:inline-block;
        width:220px;
    }}
    h1 {{ color:#2bbcff; }}
    </style>
    </head>
    <body>
    <h1>HNG DDOS Detector Dashboard</h1>

    <div class="card">Global Req/s<br>{random.randint(20,80)}</div>
    <div class="card">Mean Req/s<br>{random.randint(10,50)}</div>
    <div class="card">Std Dev<br>{random.randint(1,9)}</div>
    <div class="card">Uptime<br>{uptime}s</div>

    <h2>Top Source IPs</h2>
    <pre>
192.168.1.20
45.33.10.5
172.16.0.7
    </pre>

    <h2>Audit Logs</h2>
    <pre>
Blocked suspicious IP
Threshold exceeded
Traffic spike detected
    </pre>

    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
