#!/usr/bin/env bash
set -euo pipefail
cd /opt/radar
# Run real backup and isolated restore before enabling timers.
sudo python3 scripts/operations.py drill
sudo install -m 644 ops/systemd/radar-*.service ops/systemd/radar-*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now radar-backup.timer radar-drill.timer radar-monitor.timer
sudo systemctl list-timers 'radar-*'
