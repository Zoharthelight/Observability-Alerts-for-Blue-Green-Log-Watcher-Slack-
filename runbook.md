# Blue/Green Deployment - Operations Runbook

## Overview
This runbook describes how to respond to alerts from the Blue/Green deployment monitoring system.

---

## Alert Types

### 1. 🔄 Failover Detected

**What it means:**
Traffic has automatically switched from one pool (Blue/Green) to another due to the primary pool becoming unhealthy.

**Alert Example:**
```
🔄 Failover Detected!
- From: blue
- To: green
- Release: green-v1.0.0
- Upstream: 172.18.0.4:3000
- Time: 2025-10-30 14:23:45

⚠️ Action Required: Check health of blue service.
```

**Operator Actions:**

1. **Verify the failover:**
```bash
   # Check which pool is currently serving
   curl -i http://localhost:8080/version | grep X-App-Pool
```

2. **Investigate the failed pool:**
```bash
   # Check container status
   docker-compose ps
   
   # View logs of the failed pool
   docker-compose logs app_blue  # or app_green
```

3. **Check upstream health:**
```bash
   # Direct health check
   curl http://localhost:8081/healthz  # Blue
   curl http://localhost:8082/healthz  # Green
```

4. **Diagnose the issue:**
   - Look for application errors in container logs
   - Check resource usage: `docker stats`
   - Verify network connectivity
   - Check if chaos mode was accidentally triggered

5. **Recovery:**
   - If issue is resolved, the system will automatically fail back
   - If persistent issue, investigate application code or infrastructure
   - Consider manual restart: `docker-compose restart app_blue`

**When to escalate:**
- Failover occurs repeatedly (flapping)
- Both pools are unhealthy
- Failover during non-chaos/maintenance windows

---

### 2. 📈 High Error Rate Alert

**What it means:**
The upstream services are returning 5xx errors above the configured threshold over a sliding window of requests.

**Alert Example:**
```
📈 High Error Rate Alert!
- Error Rate: 5.50% (threshold: 2%)
- Errors: 11/200 requests
- Current Pool: green
- Window Size: 200 requests

⚠️ Action Required: Investigate upstream logs and consider manual failover.
```

**Operator Actions:**

1. **Verify the error rate:**
```bash
   # Send test requests
   for i in {1..10}; do
     curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/version
   done
```

2. **Check application logs:**
```bash
   # View real-time logs
   docker-compose logs -f app_blue app_green
   
   # Check for error patterns
   docker-compose logs app_blue | grep -i error
```

3. **Inspect Nginx logs:**
```bash
   # View detailed access logs
   docker-compose exec nginx tail -f /var/log/nginx/access.log
   
   # Check error log
   docker-compose exec nginx tail -f /var/log/nginx/error.log
```

4. **Check resource constraints:**
```bash
   # CPU and memory usage
   docker stats --no-stream
```

5. **Mitigation steps:**
   
   **Option A - Manual Failover (if one pool is healthy):**
```bash
   # Stop chaos if active
   curl -X POST http://localhost:8081/chaos/stop
   curl -X POST http://localhost:8082/chaos/stop
   
   # Check individual pool health
   curl http://localhost:8081/version
   curl http://localhost:8082/version
   
   # Restart unhealthy service
   docker-compose restart app_blue  # or app_green
```
   
   **Option B - Full Restart:**
```bash
   # Restart all services
   docker-compose restart
```
   
   **Option C - Rollback:**
```bash
   # Update .env with previous working release IDs
   # Then restart
   docker-compose down
   docker-compose up -d
```

**When to escalate:**
- Error rate persists after restart
- Both pools showing high errors
- Resource exhaustion detected
- Application-level bug suspected

---

### 3. ✅ Recovery / Healthy State

**What it means:**
The system has returned to normal operation after a failover or error condition.

**Operator Actions:**
- Monitor for stability over next 15-30 minutes
- Review incident timeline in Slack
- Document root cause if identified
- Update runbook if new issue discovered

---

## Maintenance Procedures

### Planned Maintenance (Suppress Alerts)

When performing planned maintenance or chaos testing:

1. **Enable maintenance mode:**
```bash
   # Edit .env
   echo "MAINTENANCE_MODE=true" >> .env
   
   # Restart watcher
   docker-compose restart alert_watcher
```

2. **Perform maintenance:**
```bash
   # Your maintenance tasks here
```

3. **Disable maintenance mode:**
```bash
   # Edit .env
   sed -i 's/MAINTENANCE_MODE=true/MAINTENANCE_MODE=false/' .env
   
   # Restart watcher
   docker-compose restart alert_watcher
```

---

## Manual Testing Procedures

### Test Failover Alert
```bash
# 1. Verify baseline
curl http://localhost:8080/version

# 2. Trigger chaos on Blue
curl -X POST "http://localhost:8081/chaos/start?mode=error"

# 3. Generate traffic (should trigger failover alert)
for i in {1..20}; do
  curl -s http://localhost:8080/version | grep -o '"pool":"[^"]*"'
  sleep 0.5
done

# 4. Check Slack for failover alert

# 5. Stop chaos
curl -X POST "http://localhost:8081/chaos/stop"
```

### Test Error Rate Alert
```bash
# 1. Trigger chaos with high error rate
curl -X POST "http://localhost:8081/chaos/start?mode=error"

# 2. Generate enough traffic to exceed threshold
for i in {1..250}; do
  curl -s -o /dev/null http://localhost:8080/version
  sleep 0.1
done

# 3. Check Slack for error rate alert

# 4. Stop chaos
curl -X POST "http://localhost:8081/chaos/stop"
```

---

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ERROR_RATE_THRESHOLD` | 2 | Error rate % that triggers alert |
| `WINDOW_SIZE` | 200 | Number of requests in sliding window |
| `ALERT_COOLDOWN_SEC` | 300 | Seconds between repeat alerts |
| `MAINTENANCE_MODE` | false | Suppress alerts when true |

### Adjusting Thresholds

**To make alerts more sensitive:**
```bash
# Lower error threshold
ERROR_RATE_THRESHOLD=1

# Smaller window
WINDOW_SIZE=100

# Shorter cooldown
ALERT_COOLDOWN_SEC=60
```

**To reduce alert noise:**
```bash
# Higher error threshold
ERROR_RATE_THRESHOLD=5

# Larger window
WINDOW_SIZE=500

# Longer cooldown
ALERT_COOLDOWN_SEC=600
```

---

## Troubleshooting

### Alerts Not Appearing in Slack

1. **Verify webhook URL:**
```bash
   # Check .env
   grep SLACK_WEBHOOK_URL .env
```

2. **Test webhook manually:**
```bash
   curl -X POST -H 'Content-type: application/json' \
     --data '{"text":"Test alert"}' \
     YOUR_WEBHOOK_URL
```

3. **Check watcher logs:**
```bash
   docker-compose logs alert_watcher
```

4. **Verify maintenance mode is off:**
```bash
   grep MAINTENANCE_MODE .env
```

### Watcher Not Processing Logs

1. **Check if watcher is running:**
```bash
   docker-compose ps alert_watcher
```

2. **Verify log file exists:**
```bash
   docker-compose exec nginx ls -l /var/log/nginx/
```

3. **Check watcher has access to logs:**
```bash
   docker-compose exec alert_watcher ls -l /var/log/nginx/
```

4. **Restart watcher:**
```bash
   docker-compose restart alert_watcher
   docker-compose logs -f alert_watcher
```

### False Positive Alerts

If you're getting too many alerts:

1. **Increase error threshold:**
```bash
   ERROR_RATE_THRESHOLD=5
```

2. **Increase window size:**
```bash
   WINDOW_SIZE=500
```

3. **Increase cooldown:**
```bash
   ALERT_COOLDOWN_SEC=600
```

---

## Log Analysis Commands

### View Nginx Detailed Logs
```bash
docker-compose exec nginx tail -f /var/log/nginx/access.log
```

### Extract Pool Distribution
```bash
docker-compose exec nginx grep "pool=" /var/log/nginx/access.log | \
  grep -o "pool=[a-z]*" | sort | uniq -c
```

### Count 5xx Errors
```bash
docker-compose exec nginx grep "upstream_status=5" /var/log/nginx/access.log | wc -l
```

### View Last 100 Requests
```bash
docker-compose exec nginx tail -n 100 /var/log/nginx/access.log
```

---

## Escalation Contacts

- **Primary On-Call**: [Your Name] - [Contact]
- **Secondary**: [Backup Name] - [Contact]
- **Slack Channel**: #devops-alerts
- **Incident Management**: [Your Ticketing System]

---

## Post-Incident Checklist

After resolving an incident:

- [ ] Document timeline in Slack thread
- [ ] Update .env if thresholds need adjustment
- [ ] Create post-mortem if major incident
- [ ] Update this runbook with lessons learned
- [ ] Test failover procedure to verify fix
- [ ] Notify team of resolution

---

## Additional Resources

- **Stage 2 Documentation**: README.md
- **Architecture**: DECISION.md
- **Slack Webhook Setup**: https://api.slack.com/messaging/webhooks
- **Nginx Logging**: http://nginx.org/en/docs/http/ngx_http_log_module.html

---

**Last Updated**: 2025-10-30
**Version**: 1.0
**Maintainer**: DevOps Team
