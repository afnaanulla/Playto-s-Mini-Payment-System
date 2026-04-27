# Playto Payout Engine

A production-grade, financially indestructible payout processing system built for the Playto Founding Engineer Challenge. This system handles cross-border payout logic with strict guarantees on money integrity, concurrency, and idempotency.

## Features
- **Immutable Ledger**: Every transaction is a Credit or Debit record. Balance is always derived, never stored as a mutable column.
- **Atomic Concurrency**: Prevents "Check-then-Deduct" race conditions using PostgreSQL row-level locking (`SELECT FOR UPDATE`).
- **Strict Idempotency**: Prevents duplicate payouts using a 24-hour merchant-scoped idempotency layer.
- **State Machine Payouts**: Strict lifecycle (Pending → Processing → Completed/Failed) with atomic refunds on failure.
- **Background Workers**: Async payout simulation via Celery and Redis.
- **Self-Healing**: Automatic retry of stuck payouts using exponential backoff.

---

## Tech Stack
- **Backend**: Django, Django REST Framework (DRF)
- **Database**: PostgreSQL
- **Task Queue**: Celery + Redis
- **Frontend**: React, Tailwind CSS
- **Infrastructure**: Docker & Docker Compose

---

## Setup & Installation

### 1. Prerequisites
- Docker & Docker Compose installed.

### 2. Run with Docker (Recommended)
```bash
# 1. Build and start all services (Backend, Frontend, DB, Redis, Worker, Beat)
docker-compose up --build -d

# 2. Run migrations
docker-compose exec backend python manage.py migrate

# 3. Seed initial merchant data
docker-compose exec backend python manage.py seed_data

```
The application will be available at:

Frontend: http://localhost:5173

Backend API: http://localhost:8000

### 3. Local Development (Manual)
If running without Docker, ensure you have PostgreSQL and Redis running, then:
```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Seed data
python manage.py seed_data

# Start server
python manage.py runserver

# In separate terminals:
celery -A config worker -l info
celery -A config beat -l info

cd ../frontend
npm install
npm run dev
```

### Testing
The repository includes a comprehensive test suite for the two most critical requirements: Concurrency and Idempotency.

Run automated tests:
Ensure the server is running, then execute:

```
python concurrency_test.py
```

Note: This script dynamically finds seeded merchants and executes parallel threads to simulate race conditions.