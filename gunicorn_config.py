import os
import multiprocessing

# Bind to platform-provided port (Heroku/Render/Cloud Run) or default 8080
bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"

# Reasonable defaults; allow overrides via env
workers = int(os.environ.get("WEB_CONCURRENCY", max(1, multiprocessing.cpu_count() // 2)))
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "gevent")

# Logging
loglevel = os.environ.get("LOG_LEVEL", "info")
accesslog = '-'  # stdout
errorlog = '-'   # stderr