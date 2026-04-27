# Playto Payout Engine

A production-grade, financially indestructible payout processing system built for the Playto Founding Engineer Challenge. This system handles cross-border payout logic with strict guarantees on money integrity, concurrency, and idempotency.

---

## 🧪 Testing (Concurrency & Idempotency)

The repository includes a comprehensive test suite for the two most critical requirements. To run these, ensure the Docker containers are running, then execute:

```bash
venv\Scripts\activate
python concurrency_test.py
```

*Note: This script dynamically finds seeded merchants and executes parallel threads to simulate race conditions.*

---

## 📦 Setup & Installation (Docker)

This is the fastest way to start all services (Database, Redis, Workers, API, and Frontend).

```bash
# 1. Build and start all services
docker-compose up --build -d

# 2. Run migrations
docker-compose exec web python manage.py migrate

# 3. Seed initial merchant data
docker-compose exec web python manage.py seed_data
```

---

## 📊 Viewing Logs (Monitoring the Engine)

To see the background workers, the API, or the scheduler in real-time, use these commands:

```bash
# To see the Worker (Payout Processor) only
docker-compose logs -f worker

# To see the Watchdog (Celery Beat) only
docker-compose logs -f beat

# To see the Web (Django API) only
docker-compose logs -f web

# To see the Worker and the Beat together (Recommended)
docker-compose logs -f worker beat

# To see all logs from every container
docker-compose logs -f
```

---

## 🏗️ Core Background Services (Celery & Redis)

To simulate a real-world payment system, this project separates the **Request** from the **Processing**:

1.  **Redis (The Broker)**: Acts as the message queue. When you click "Initiate Payout", the API sends a secure task to Redis.
2.  **Celery Worker (The Processor)**: The actual engine. It picks up tasks from Redis, simulates bank settlements (Success/Fail/Hang), and updates the database.
3.  **Celery Beat (The Watchdog)**: A scheduler that runs every 15 seconds. It looks for any payout stuck in "Processing" for too long and triggers an automatic retry. **Without Beat, the self-healing retry logic will not run.**

---

## 📄 Documentation

For a deep dive into the engineering decisions and AI-driven architectural audits, see [EXPLAINER.md](./EXPLAINER.md).
