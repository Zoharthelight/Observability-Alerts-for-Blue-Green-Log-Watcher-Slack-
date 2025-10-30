

#  Blue/Green Deployment with Nginx (Docker Compose)

This project implements a **Blue/Green deployment strategy** using **Docker Compose** and **Nginx upstreams**.
It enables **zero-downtime failover** between two identical Node.js services — Blue (active) and Green (backup) — based on health and manual toggles.

---

##  Quick Start

### 1. Setup Environment

Copy the example environment file and edit values:

```bash
cp .env.example .env
# Edit .env and set:
# BLUE_IMAGE=<blue image>
# GREEN_IMAGE=<green image>
# RELEASE_ID_BLUE=<blue release id>
# RELEASE_ID_GREEN=<green release id>
# ACTIVE_POOL=blue
```

---

### 2. Start the Stack

```bash
docker-compose up -d
```

---

### 3. Verify Baseline (Blue Active)

Check version endpoint:

```bash
curl -i http://localhost:8080/version
```

Expected headers:

```
X-App-Pool: blue
X-Release-Id: <release_id_blue>
```

---

### 4. Simulate Downtime on Blue

```bash
curl -X POST "http://localhost:8081/chaos/start?mode=error"
# or
curl -X POST "http://localhost:8081/chaos/start?mode=timeout"
```

---

### 5. Verify Failover

While chaos is active:

```bash
./verify_failover.sh
```

Expected behavior:

* Requests return 200 OK
* `X-App-Pool` switches to **green**

---

### 6. Stop Chaos

```bash
curl -X POST "http://localhost:8081/chaos/stop"
```

---

### 7. Manually Switch Active Pool (Optional)

```bash
# switch to green
docker-compose exec -e ACTIVE_POOL=green nginx /docker-entrypoint.sh reload

# switch back to blue
docker-compose exec -e ACTIVE_POOL=blue nginx /docker-entrypoint.sh reload
```

---

### 8. Stop Everything

```bash
docker-compose down
```

---

##  Key Concepts

* **Blue/Green Deployment** → Two identical environments (Blue active, Green standby) for zero-downtime updates.
* **Nginx Failover** → Automatically switches traffic to the healthy upstream.
* **Docker Compose** → Orchestrates all containers and environment variables.

---

##  Project Structure

```
├── docker-compose.yml
├── nginx/
│   ├── nginx.conf.template
├── .env.example
├── verify_failover.sh
└── README.md
```

---
cat > README.md << 'EOF'
# Blue/Green Deployment with Observability & Slack Alerts

## Overview
This project implements a blue/green deployment strategy with Nginx auto-failover, real-time log monitoring, and Slack alerting for operational visibility.

## Features
- ✅ Blue/Green deployment with automatic failover
- ✅ Real-time log monitoring with Python watcher
- ✅ Slack alerts for failovers and high error rates
- ✅ Structured Nginx logging with pool, release, and upstream info
- ✅ Configurable thresholds and alert cooldowns
- ✅ Maintenance mode for suppressing alerts

## Architecture
```
┌─────────────┐
│   Requests  │
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌──────────────┐
│    Nginx    │◄────►│ Log Watcher  │
│   (8080)    │      │   (Python)   │
└──────┬──────┘      └──────┬───────┘
       │                    │
       │                    │ Slack Webhook
   ┌───┴────┐               ▼
   │        │         ┌──────────────┐
   ▼        ▼         │    Slack     │
┌────┐  ┌────┐        │   Channel    │
│Blue│  │Green│       └──────────────┘
│8081│  │8082│
└────┘  └────┘
```

## Prerequisites
- Docker & Docker Compose
- Slack workspace with incoming webhook
- Stage 2 project completed

## Quick Start

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd Blue-Green-Deployment-Project-main
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env and add your SLACK_WEBHOOK_URL
nano .env
```

### 3. Start Services
```bash
docker-compose up -d

# Wait for services to be ready
sleep 15

# Verify all containers are running
docker-compose ps
```

### 4. Test Baseline
```bash
curl -i http://localhost:8080/version
```

Expected headers:
```
X-App-Pool: blue
X-Release-Id: blue-v1.0.0
```

## Testing Failover & Alerts

### Test 1: Failover Alert
```bash
# 1. Trigger chaos on Blue
curl -X POST "http://localhost:8081/chaos/start?mode=error"

# 2. Generate traffic to trigger failover
for i in {1..20}; do
  curl -s http://localhost:8080/version | grep -o '"pool":"[^"]*"'
  sleep 0.5
done

# 3. Check Slack for "Failover Detected" alert

# 4. Stop chaos
curl -X POST "http://localhost:8081/chaos/stop"
```

**Expected:** Slack alert showing Blue → Green failover

### Test 2: High Error Rate Alert
```bash
# 1. Trigger chaos
curl -X POST "http://localhost:8081/chaos/start?mode=error"

# 2. Generate enough traffic to exceed error threshold
for i in {1..250}; do
  curl -s -o /dev/null http://localhost:8080/version
  sleep 0.1
done

# 3. Check Slack for "High Error Rate Alert"

# 4. Stop chaos
curl -X POST "http://localhost:8081/chaos/stop"
```

**Expected:** Slack alert showing error rate > 2%

## Viewing Logs

### Nginx Structured Logs
```bash
# View access logs with pool info
docker-compose exec nginx tail -f /var/log/nginx/access.log

# View error logs
docker-compose exec nginx tail -f /var/log/nginx/error.log
```

### Watcher Logs
```bash
docker-compose logs -f alert_watcher
```

### Application Logs
```bash
# Blue service
docker-compose logs -f app_blue

# Green service
docker-compose logs -f app_green
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BLUE_IMAGE` | - | Docker image for Blue |
| `GREEN_IMAGE` | - | Docker image for Green |
| `ACTIVE_POOL` | blue | Initial active pool |
| `RELEASE_ID_BLUE` | blue-v1.0.0 | Blue release ID |
| `RELEASE_ID_GREEN` |


