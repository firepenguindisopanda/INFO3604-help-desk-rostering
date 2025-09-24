import os
import multiprocessing

# Bind to platform-provided port (Heroku/Render/Cloud Run) or default 8000
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Reasonable defaults; allow overrides via env
workers = int(os.environ.get("WEB_CONCURRENCY", 4))
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "gevent")

# Timeout configuration for Render free tier
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))  # 2 minutes instead of default 30s
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", 5))
worker_connections = int(os.environ.get("GUNICORN_WORKER_CONNECTIONS", 1000))

# Memory and process management
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", 1000))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", 100))
preload_app = True

# Logging
loglevel = os.environ.get("LOG_LEVEL", "info")
accesslog = '-'  # stdout
errorlog = '-'   # stderr