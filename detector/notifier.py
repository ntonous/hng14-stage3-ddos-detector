import json
import urllib.request
import yaml

with open("../config.yaml") as f:
    config = yaml.safe_load(f)

WEBHOOK = config.get("slack_webhook", "").strip()

def send_slack(message):
    if not WEBHOOK:
        return

    data = json.dumps({"text": message}).encode("utf-8")

    req = urllib.request.Request(
        WEBHOOK,
        data=data,
        headers={"Content-Type": "application/json"}
    )

    try:
        urllib.request.urlopen(req, timeout=5)
        print("Slack alert sent")
    except Exception as e:
        print("Slack error:", e)
