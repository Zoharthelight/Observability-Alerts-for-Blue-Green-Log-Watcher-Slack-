

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

