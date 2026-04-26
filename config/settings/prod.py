from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Production security settings

# Only allow specific hosts
# In production, we'll allow all hosts to prevent 400 errors from Render's health checks
# but you should restrict this to your actual domain if you want more security.
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

# CORS - allow the frontend domain
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'https://playto-payout.vercel.app',
    'https://playto-s-mini-payment-system-1.onrender.com', # Added Render frontend
])
CORS_ALLOW_ALL_ORIGINS = False

# CSRF settings
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[
    'https://playto-payout.vercel.app',
    'https://playto-s-mini-payment-system-1.onrender.com',
])

# Security settings for production
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True  # Redirect all HTTP to HTTPS
SESSION_COOKIE_SECURE = True  # Cookies only sent over HTTPS
CSRF_COOKIE_SECURE = True  # CSRF cookie only sent over HTTPS
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

X_FRAME_OPTIONS = 'DENY'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'payouts': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
