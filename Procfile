# Procfile for Railway/Heroku deployment
# Defines the processes that run the application

# Web server - handles HTTP requests with limited workers to save memory
web: gunicorn config.wsgi:application --workers 1 --threads 2 --bind 0.0.0.0:$PORT

# Celery worker + beat - combined into one process with solo pool for 512MB RAM limit
worker: celery -A config worker --concurrency=1 --pool=solo -B --loglevel=info
