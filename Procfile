# Procfile for Railway/Heroku deployment
# Defines the processes that run the application

# Web server - handles HTTP requests
web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT

# Celery worker - processes background payout tasks
worker: celery -A config worker --loglevel=info

# Celery beat - scheduler for periodic tasks (retry_stuck_payouts every 15s)
beat: celery -A config beat --loglevel=info
