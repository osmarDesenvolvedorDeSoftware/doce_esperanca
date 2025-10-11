"""Gunicorn configuration for the Doce Esperança application.

This configuration switches the worker class to the threaded implementation so a
single slow client does not block an entire worker process. It also increases
timeouts slightly to give the application enough time to finish legitimate
requests while keeping idle connections from hanging indefinitely.
"""

import multiprocessing

# Allow each worker process to serve multiple requests concurrently.
worker_class = "gthread"
threads = 4

# Start a sensible number of workers based on available CPU cores.
workers = multiprocessing.cpu_count() * 2 + 1

# Tune connection handling to mitigate slow clients without killing workers too quickly.
keepalive = 5
timeout = 60

# Restart workers periodically to avoid memory bloat in long-running processes.
max_requests = 500
max_requests_jitter = 50

