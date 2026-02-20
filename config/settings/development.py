from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']

# Use SQLite for development (easy setup)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Use local memory cache for development (no Redis required)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# CORS for development
CORS_ALLOW_ALL_ORIGINS = True

# Email backend for development (console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable Slack in development unless explicitly set
if not SLACK_WEBHOOK_URL:
    SLACK_WEBHOOK_URL = None

# Run Celery tasks synchronously in development
CELERY_TASK_ALWAYS_EAGER = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'leads': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
