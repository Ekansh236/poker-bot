# One image, every role. The app (daphne), the Celery worker, Celery Beat,
# and Flower all run this exact same image in docker-compose.yml -- only
# the CMD differs per service -- instead of maintaining near-duplicate
# Dockerfiles for code that's identical except for which process starts.
FROM python:3.10-slim

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

# No CMD here -- docker-compose.yml sets one explicitly per service
# (daphne for web, `celery worker`/`beat`/`flower` for the others), since
# there's no single sensible default across four different roles.
