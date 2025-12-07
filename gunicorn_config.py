# Configuration Gunicorn optimisée pour Socket.IO sur Render free tier
import os

# Bind
bind = f"0.0.0.0:{os.environ.get('PORT', '5001')}"

# Workers (IMPORTANT: 1 seul worker pour Socket.IO)
workers = 1
worker_class = "eventlet"
worker_connections = 1000

# Timeouts (augmentés pour Socket.IO)
timeout = 120
keepalive = 5
graceful_timeout = 30

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "quiz-game"

# Memory optimization
max_requests = 1000  # Redémarre le worker après 1000 requêtes pour libérer la RAM
max_requests_jitter = 50

# Preload (désactivé pour économiser la RAM)
preload_app = False
