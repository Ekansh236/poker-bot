# Real-Time Multiplayer Poker, Analytics & Autonomous Bot Platform

A high-concurrency, real-time Texas Hold'em platform built to demonstrate distributed-systems
fundamentals: real-time WebSocket state sync, Redis-backed pub/sub and distributed locking, and
autonomous decision-making via Monte Carlo simulation.

This is an active learning project — every line of domain/business logic is written and debugged
by hand; framework boilerplate and infra glue are the only parts scaffolded directly.

## Current status

| Milestone | Status |
|---|---|
| 1. Data modeling | In progress — real Postgres DB wired up, `accounts` app scaffolded; User/Table/Hand/Balance models not yet written |
| 2. Pure Python Texas Hold'em engine | Complete — 59 passing tests |
| 3. Real-time WebSockets + Redis game state | Complete — verified live with real WebSocket connections |
| 4. Autonomous bot engine (Monte Carlo + pot odds + real Celery dispatch) | Complete |
| 4.5. Blinds, button rotation, position-aware bot decisions, live auto-advancement | Complete |
| 5. Celery Beat turn-timeouts, structlog, Flower monitoring | Complete |
| 6. Stripe/VIP tiers | Dropped — no real payments in this project |
| 7-9. AI coach, React frontend, Docker/CI | Not started |

Also built ahead of schedule: a minimal local play UI (`table/templates/table/play.html`) to actually
play a full game against the bot in a browser, independent of the real Milestone 8 React frontend.

## Architecture

```
Client (WebSocket)
      │  ws://.../ws/table/<table_id>/<player_id>/
      ▼
config/asgi.py ──► table/routing.py ──► table/consumers.py (TableConsumer)
                                               │
                                ┌──────────────┼──────────────┐
                                ▼                              ▼
                      table/registry.py                table/serializers.py
                      (Redis-backed locked_round)       (Round → JSON-safe dict)
                                │
                                ▼
                        poker_engine/round.py
                      (pure Python game engine)

                                │  bot_decide_task.delay() / Celery Beat tick
                                ▼
                        table/tasks.py (Celery worker, separate process)
                          ├─ bot_decide_task      -- Monte Carlo bot decision
                          └─ check_turn_timeouts  -- periodic auto-fold on inactivity
                                │
                                ▼
                        Flower (celery -A config flower) -- queue/task monitoring
```

- **`poker_engine/`** — framework-agnostic Texas Hold'em domain engine: cards, hand evaluation,
  betting rounds, blinds, button rotation, side pots, showdown resolution, hand orchestration
  (`Round.apply_action_and_advance()`), and the autonomous bot's Monte Carlo equity simulator and
  position-aware pot-odds decision logic. No Django/Channels dependency — this is intentional, so
  the same engine can sit behind a WebSocket, a REST API, or a bot without modification.
- **`table/`** — the Django Channels real-time layer. `TableConsumer` handles WebSocket
  connections; `registry.py` stores live game state in Redis behind a distributed lock
  (`locked_round()`), preventing the classic multi-worker "lost update" race condition where two
  server processes both read stale state and one silently overwrites the other's write.
  `tasks.py` holds the Celery tasks that run on a separate worker process: dispatching bot
  decisions and periodically auto-folding players who've gone idle.
- **`config/`** — Django project settings, ASGI routing, Redis-backed channel layer config, Celery
  app + Beat schedule, structlog configuration.

## Notable engineering details

- **Distributed locking, not just caching.** `table/registry.py`'s `locked_round()` is a context
  manager that acquires a Redis lock, deserializes the `Round`, hands it to the caller, and
  guarantees the mutated state is written back (via `try/finally`) even if the caller raises —
  verified with a live test that the lock releases and the write survives an injected exception.
- **Opponent-safe, JSON-safe serialization.** `table/serializers.py` deliberately excludes hole
  cards from the broadcast payload sent to the whole table, while still exposing everything a
  client needs to render live state (pot, current turn, community cards, per-seat public info).
- **Monte Carlo hand equity, not a lookup table.** `poker_engine/bot.py`'s `estimate_equity()`
  simulates thousands of random deck completions and reuses the Milestone 2 hand evaluator to
  estimate win probability — built from a fresh, full 52-card deck each time rather than a live
  `Round`'s `Deck`, so the bot can never "see" which cards opponents are holding.
- **A single choke point for every state mutation.** `Round.apply_action_and_advance()` pairs
  `apply_action()` with `advance_if_possible()` so every caller (the WebSocket consumer, the bot
  task, the turn-timeout task) automatically cascades through street transitions, fold-wins, and
  new-hand dealing — impossible to forget, unlike calling the two separately.
- **Pickle's schema-evolution trap.** Game state is `pickle`d into Redis, which restores an
  object's saved `__dict__` directly rather than re-running `__init__()`. Adding a new field to
  `Round` (e.g. `time_started`) means every *already-persisted* Round silently lacks it —
  `check_turn_timeouts()` guards against this with `getattr(round_, "time_started", 0)` rather
  than crashing the periodic sweep over one stale table.

## Tech stack

Python · Django · Django Channels · Redis · Celery + Celery Beat · Flower · structlog ·
PostgreSQL (planned) · React/TypeScript (planned) · pytest

## Running it locally

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Start Redis (macOS/Homebrew)
brew services start redis

# Run the test suite
pytest

# Run the dev server (WebSocket-capable, via daphne)
python manage.py runserver

# Run a Celery worker (bot decisions + turn-timeout auto-folds) -- separate
# terminal. --pool=solo works around a macOS-specific prefork-pool crash,
# unrelated to application code.
celery -A config worker --pool=solo --loglevel=info

# Run Celery Beat (fires check_turn_timeouts every 5s) -- separate terminal
celery -A config beat --loglevel=info

# Run Flower (queue/task monitoring dashboard) -- separate terminal
celery -A config flower --port=5555
```

WebSocket tables are reachable directly at `ws://localhost:8000/ws/table/<table_id>/<player_id>/`,
or play a full game in a browser at `http://localhost:8000/play/<table_id>/<player_id>/` (e.g.
`http://localhost:8000/play/table1/alice/`) — `table_id`/`player_id` are arbitrary names you choose.
Redis, `runserver`, and a Celery worker are required to actually play. Beat is required too for
the 15s inactivity auto-fold to actually fire (`celery -A config beat`, its own process, separate
from the worker) -- the game still runs without it, just with that one feature silently inert.
Flower is a genuinely optional monitoring dashboard.
Flower's dashboard is at `http://localhost:5555`.

## Known gaps (tracked, not hidden)

- No real database yet — `table/models.py` is empty and `settings.py` still points at the default
  SQLite file. Milestone 1 was conceptual/architectural, not actual Django models. Needed before
  Milestone 6 (Stripe/VIP tiers) or any real user accounts.
- `poker_engine/starting_hands.py`'s 169-hand preflop strength chart is built but not wired into
  `decide_action()` — the bot currently decides preflop raises purely from Monte Carlo equity.
- Bankroll/elimination is minimal — `Round.game_over` correctly ends a heads-up game once a seat
  hits 0 chips (no infinite loop dealing a broke player into hands they can't fund), but there's
  no multi-table bankroll persistence beyond that; the play UI's Restart button is the only way
  back to a fresh 500/500 game.
