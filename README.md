README.md
# Building a Lightweight DDoS Detection Dashboard with Python and Flask

For HNG Stage 3, I built a lightweight DDoS monitoring system that simulates real-time attack detection and traffic monitoring.

## Goal

Create a public dashboard that shows:

- Requests per second
- Source IP addresses
- Uptime
- Audit logs

## Tools Used

- Python Flask
- Ubuntu Linux VPS
- Nginx Reverse Proxy
- GitHub

## Challenges I Faced

The hardest part was reverse proxy configuration.  
Initially Nginx pointed to wrong ports, causing old dashboards and bad gateway errors.

I fixed it by:

- Updating Nginx config
- Restarting services
- Rebuilding Flask app

## Final Result

Live URL:

http://metrics.ntscomputers.dpdns.org

GitHub Repo:

https://github.com/ntonous/hng14-stage3-ddos-detector

## Lessons Learned

I learned Linux deployment, Nginx routing, Flask production hosting, and debugging under pressure.

This project improved my DevOps confidence greatly.
