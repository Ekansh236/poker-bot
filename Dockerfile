# One image, every role. The app (daphne), the Celery worker, Celery Beat,
# and Flower all run this exact same image in docker-compose.yml -- only
# the CMD differs per service -- instead of maintaining near-duplicate
# Dockerfiles for code that's identical except for which process starts.
#
# redis-server is installed here too, unused by any docker-compose service
# (that still runs its own separate redis:7-alpine container) -- it exists
# for bin/start-fly.sh, which runs Redis IN-PROCESS alongside daphne/worker/
# beat so a single $5-10/mo Fly machine can host the whole app instead of
# paying for a separate machine per process (see bin/start-fly.sh's own
# comment for why that's safe for this app's specific use of Redis).
FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends redis-server \
    && rm -rf /var/lib/apt/lists/*

# Keeps Python from buffering stdout/stderr -- logs show up immediately in
# `docker compose logs` instead of waiting on a buffer flush.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Dependencies change far less often than application code -- a separate
# COPY+install layer means editing a .py file doesn't invalidate pip's
# layer cache and force a full reinstall on every rebuild.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x bin/start-fly.sh

# No CMD here -- docker-compose.yml sets one explicitly per service (daphne
# for web, `celery worker`/`beat`/`flower` for the others) and fly.toml
# sets bin/start-fly.sh for the deployed app, since there's no single
# sensible default across every role this one image can play.
