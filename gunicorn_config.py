import os
import multiprocessing

# Bind to platform-provided port (Heroku/Render/Cloud Run) or default 8000
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Reasonable defaults; allow overrides via env
workers = int(os.environ.get("WEB_CONCURRENCY", 4))
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "gevent")

# Logging
loglevel = os.environ.get("LOG_LEVEL", "info")
accesslog = '-'  # stdout
errorlog = '-'   # stderr