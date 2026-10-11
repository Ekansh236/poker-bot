#!/bin/bash
# `wait -n` below needs real bash, not /bin/sh (dash on Debian) -- it's a
# bash-only feature.
#
# Entrypoint for the deployed Fly app -- runs every process (Redis, the
# web app, the Celery worker, Celery Beat) on ONE machine instead of
# paying for four separate ones, the way docker-compose.yml's four
# services do locally.
#
# Running Redis in-process like this is only safe because of what THIS
# app actually stores in it: live game state (table/registry.py), the
# Channels pub/sub layer, and the Celery broker/result backend -- all of
# it ephemeral or already-regenerable, never the durable record of a
# played hand (that's Postgres, via table/models.py, which still runs as
# Fly's own separately-managed, properly backed-up Postgres app). Losing
# Redis on a machine restart means losing in-progress hands, not game
# history -- an acceptable trade for a friends-hobby deployment, not one
# this script would make for data that actually needs to survive a crash.
set -eu

redis-server --bind 127.0.0.1 --daemonize no &
REDIS_PID=$!

# Signals Fly sends on deploy/restart (SIGTERM) must reach every child,
# not just whichever process this script happens to be waiting on --
# otherwise Celery's worker/beat linger as orphans after the container
# "exits".
trap 'kill $REDIS_PID $DAPHNE_PID $WORKER_PID $BEAT_PID 2>/dev/null' TERM INT

# redis-server daemonizing=no still returns control to this script
# immediately -- wait for it to actually accept connections before
# anything tries to use it as the Channels layer / Celery broker.
until redis-cli -h 127.0.0.1 ping >/dev/null 2>&1; do
  sleep 0.2
done

python manage.py migrate --noinput

daphne -b 0.0.0.0 -p 8000 config.asgi:application &
DAPHNE_PID=$!
celery -A config worker --loglevel=info &
WORKER_PID=$!
celery -A config beat --loglevel=info &
BEAT_PID=$!

# Any one of these dying is treated as the whole machine failing -- Fly
# restarts the container, which cleanly restarts all four processes
# together, rather than silently limping along with (say) a dead worker
# and bots that never act again.
wait -n $REDIS_PID $DAPHNE_PID $WORKER_PID $BEAT_PID
