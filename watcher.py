#!/usr/bin/env python3
"""
Nginx Log Watcher for Blue/Green Deployment
Monitors Nginx access logs and sends Slack alerts on:
1. Failover events (pool changes)
2. High error rates (5xx responses)
"""

import os
import re
import time
import json
import requests
from collections import deque
from datetime import datetime, timedelta

# Configuration from environment variables
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
ERROR_RATE_THRESHOLD = float(os.getenv('ERROR_RATE_THRESHOLD', 2.0))
WINDOW_SIZE = int(os.getenv('WINDOW_SIZE', 200))
ALERT_COOLDOWN_SEC = int(os.getenv('ALERT_COOLDOWN_SEC', 300))
MAINTENANCE_MODE = os.getenv('MAINTENANCE_MODE', 'false').lower() == 'true'
LOG_FILE = '/var/log/nginx/access.log'

# State tracking
last_pool = None
request_window = deque(maxlen=WINDOW_SIZE)
last_alert_times = {
    'failover': None,
    'error_rate': None
}


def parse_log_line(line):
    """
    Parse Nginx log line to extract relevant fields
    Returns: dict with pool, release, status, upstream_status, etc.
    """
    try:
        # Extract pool
        pool_match = re.search(r'pool=(\w+)', line)
        pool = pool_match.group(1) if pool_match else 'unknown'

        # Extract release
        release_match = re.search(r'release=([\w\-\.]+)', line)
        release = release_match.group(1) if release_match else 'unknown'

        # Extract upstream status
        upstream_status_match = re.search(r'upstream_status=(\d+)', line)
        upstream_status = int(upstream_status_match.group(1)) if upstream_status_match else 0

        # Extract HTTP status
        status_match = re.search(r'"[A-Z]+\s+[^"]+"\s+(\d+)', line)
        status = int(status_match.group(1)) if status_match else 0

        # Extract upstream address
        upstream_match = re.search(r'upstream=([\d\.:]+)', line)
        upstream = upstream_match.group(1) if upstream_match else 'unknown'

        # Extract request time
        request_time_match = re.search(r'request_time=([\d\.]+)', line)
        request_time = float(request_time_match.group(1)) if request_time_match else 0.0

        return {
            'pool': pool,
            'release': release,
            'status': status,
            'upstream_status': upstream_status,
            'upstream': upstream,
            'request_time': request_time,
            'is_5xx': status >= 500 or upstream_status >= 500,
            'timestamp': datetime.now()
        }
    except Exception as e:
        print(f"Error parsing log line: {e}")
        return None


def send_slack_alert(message, alert_type='info'):
    """Send alert to Slack"""
    if not SLACK_WEBHOOK_URL or MAINTENANCE_MODE:
        print(f"Alert suppressed (maintenance={MAINTENANCE_MODE}): {message}")
        return

    # Check cooldown
    if last_alert_times.get(alert_type):
        time_since_last = (datetime.now() - last_alert_times[alert_type]).total_seconds()
        if time_since_last < ALERT_COOLDOWN_SEC:
            print(f"Alert in cooldown ({time_since_last:.0f}s < {ALERT_COOLDOWN_SEC}s): {message}")
            return

    # Color coding
    colors = {
        'failover': '#FFA500',  # Orange
        'error_rate': '#FF0000',  # Red
        'recovery': '#00FF00',  # Green
        'info': '#0000FF'  # Blue
    }

    color = colors.get(alert_type, '#808080')

    payload = {
        "attachments": [{
            "color": color,
            "title": f"🚨 Blue/Green Alert - {alert_type.upper()}",
            "text": message,
            "footer": "DevOps Monitoring",
            "ts": int(time.time())
        }]
    }

    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        response.raise_for_status()
        print(f"✓ Slack alert sent: {message}")
        last_alert_times[alert_type] = datetime.now()
    except Exception as e:
        print(f"✗ Failed to send Slack alert: {e}")


def check_failover(parsed_data):
    """Detect pool failover"""
    global last_pool

    current_pool = parsed_data['pool']

    if current_pool == 'unknown':
        return

    if last_pool is None:
        last_pool = current_pool
        print(f"Initial pool detected: {current_pool}")
        return

    if current_pool != last_pool:
        message = (
            f"🔄 **Failover Detected!**\n"
            f"• From: `{last_pool}`\n"
            f"• To: `{current_pool}`\n"
            f"• Release: `{parsed_data['release']}`\n"
            f"• Upstream: `{parsed_data['upstream']}`\n"
            f"• Time: {parsed_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"⚠️ **Action Required:** Check health of `{last_pool}` service."
        )
        send_slack_alert(message, alert_type='failover')
        last_pool = current_pool


def check_error_rate(parsed_data):
    """Monitor error rate over sliding window"""
    request_window.append(parsed_data)

    if len(request_window) < WINDOW_SIZE:
        return  # Not enough data yet

    # Count 5xx errors in window
    error_count = sum(1 for req in request_window if req['is_5xx'])
    error_rate = (error_count / len(request_window)) * 100

    if error_rate > ERROR_RATE_THRESHOLD:
        message = (
            f"📈 **High Error Rate Alert!**\n"
            f"• Error Rate: `{error_rate:.2f}%` (threshold: {ERROR_RATE_THRESHOLD}%)\n"
            f"• Errors: `{error_count}/{len(request_window)}` requests\n"
            f"• Current Pool: `{parsed_data['pool']}`\n"
            f"• Window Size: `{WINDOW_SIZE}` requests\n\n"
            f"⚠️ **Action Required:** Investigate upstream logs and consider manual failover."
        )
        send_slack_alert(message, alert_type='error_rate')


def tail_log_file():
    """Tail the Nginx log file and process new lines"""
    print(f"Starting log watcher...")
    print(f"  Log file: {LOG_FILE}")
    print(f"  Error threshold: {ERROR_RATE_THRESHOLD}%")
    print(f"  Window size: {WINDOW_SIZE}")
    print(f"  Cooldown: {ALERT_COOLDOWN_SEC}s")
    print(f"  Maintenance mode: {MAINTENANCE_MODE}")

    # Wait for log file to exist
    while not os.path.exists(LOG_FILE):
        print(f"Waiting for log file: {LOG_FILE}")
        time.sleep(5)

    print(f"✓ Log file found. Monitoring...")

    with open(LOG_FILE, 'r') as f:
        # Try to seek to end of file (skip existing logs)
        # If not seekable, we'll just start from the beginning
        try:
            f.seek(0, 2)
            print("Seeking to end of log file...")
        except (OSError, IOError) as e:
            print(f"Log file not seekable, starting from beginning: {e}")

        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue

            parsed = parse_log_line(line)
            if parsed:
                check_failover(parsed)
                check_error_rate(parsed)


if __name__ == '__main__':
    if not SLACK_WEBHOOK_URL:
        print("WARNING: SLACK_WEBHOOK_URL not set. Alerts will be logged only.")

    tail_log_file()
