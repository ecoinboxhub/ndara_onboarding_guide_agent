"""
Gunicorn configuration for production deployment
"""
import multiprocessing
import os

# Server socket
bind = f"{os.getenv('API_HOST', '0.0.0.0')}:{os.getenv('API_PORT', 8000)}"
backlog = 2048

# Worker processes
workers = int(os.getenv('WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = os.getenv('LOG_LEVEL', 'info').lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'customer-ai'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = None
# certfile = None

# Performance tuning
max_requests = 1000
max_requests_jitter = 50
preload_app = True

def when_ready(server):
    """Called just after the server is started"""
    server.log.info("Customer AI server is ready. Spawning workers")

def on_exit(server):
    """Called just before exiting"""
    server.log.info("Customer AI server is shutting down")

