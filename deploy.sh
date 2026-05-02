#!/bin/bash
# ============================================================
# deploy.sh — Deploy HNG DDoS Detector from scratch
# Run from: ~/hng14-stage3-ddos-detector/
# ============================================================
set -e

echo "==> Stopping old containers..."
docker compose down --remove-orphans 2>/dev/null || docker-compose down --remove-orphans 2>/dev/null || true

echo "==> Removing old detector image to force rebuild..."
docker rmi hng14-stage3-ddos-detector-detector 2>/dev/null || true
docker rmi hng14-stage3-ddos-detector_detector 2>/dev/null || true

echo "==> Creating logs directory..."
mkdir -p logs

echo "==> Checking SLACK_WEBHOOK env var..."
if [ -z "$SLACK_WEBHOOK" ]; then
    echo "WARNING: SLACK_WEBHOOK not set. Slack alerts will be skipped."
    echo "Run: export SLACK_WEBHOOK=https://hooks.slack.com/services/..."
fi

echo "==> Building and starting all services..."
docker compose up -d --build 2>/dev/null || docker-compose up -d --build

echo "==> Waiting 10s for containers to start..."
sleep 10

echo "==> Container status:"
docker ps -a

echo "==> Detector logs:"
docker logs hng-detector --tail 30

echo ""
echo "✅ Deployment complete!"
echo "   Nextcloud : http://52.233.247.107"
echo "   Dashboard : http://metrics.ntscomputers.dpdns.org"
echo "   Logs      : docker logs hng-detector -f"
