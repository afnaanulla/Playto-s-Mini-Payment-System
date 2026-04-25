from .base import *

# Debug mode for local development
DEBUG = True

# Local development database (SQLite by default, can override with DATABASE_URL)
DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/db.sqlite3')
}

# Allow all CORS origins for local development
CORS_ALLOW_ALL_ORIGINS = True

# Allow all hosts in development
ALLOWED_HOSTS = ['*']

# Disable security redirects for local development
SECURE_SSL_REDIRECT = False

# Console email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
