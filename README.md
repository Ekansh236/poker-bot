# Real-Time Multiplayer Poker, Analytics & Autonomous Bot Platform

A high-concurrency, real-time Texas Hold'em platform built to demonstrate distributed-systems
fundamentals: real-time WebSocket state sync, Redis-backed pub/sub and distributed locking, and
autonomous decision-making via Monte Carlo simulation.

This is an active learning project — every line of domain/business logic is written and debugged
by hand; framework boilerplate and infra glue are the only parts scaffolded directly.

## Current status

| Milestone | Status |
|---|---|
| 1. Data modeling | Complete |
| 2. Pure Python Texas Hold'em engine | Complete — 57 passing tests |
| 3. Real-time WebSockets + Redis game state | Complete — verified live with real WebSocket connections |
| 4. Autonomous bot engine (Monte Carlo + pot odds) | In progress |
| 4.5. Blinds, button rotation, real position (planned) | Not started |
| 5-9. Celery, Stripe, AI coach, React frontend, Docker/CI | Not started |

## Architecture

```
Client (WebSocket)
      │  ws://.../ws/table/<table_id>/<player_id>/
      ▼
config/asgi.py  ──►  table/routing.py  ──►  table/consumers.py (TableConsumer)
                                                   │
                                    ┌──────────────┼──────────────┐
                                    ▼                              ▼
                          table/registry.py                table/serializers.py
                          (Redis-backed locked_round)       (Round → JSON-safe dict)
                                    │
                                    ▼
                            poker_engine/round.py
                          (pure Python game engine)
```

- **`poker_engine/`** — framework-agnostic Texas Hold'em domain engine: cards, hand evaluation,
  betting rounds, side pots, showdown resolution, and (in progress) the autonomous bot's Monte
  Carlo equity simulator and pot-odds decision logic. No Django/Channels dependency — this is
  intentional, so the same engine can sit behind a WebSocket, a REST API, or a bot without
  modification.
- **`table/`** — the Django Channels real-time layer. `TableConsumer` handles WebSocket
  connections; `registry.py` stores live game state in Redis behind a distributed lock
  (`locked_round()`), preventing the classic multi-worker "lost update" race condition where two
  server processes both read stale state and one silently overwrites the other's write.
- **`config/`** — Django project settings, ASGI routing, Redis-backed channel layer config.

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

## Tech stack

Python · Django · Django Channels · Redis · PostgreSQL (planned) · Celery (planned) ·
React/TypeScript (planned) · pytest

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
```

WebSocket tables are reachable at `ws://localhost:8000/ws/table/<table_id>/<player_id>/`.

## Known gaps (tracked, not hidden)

- No blind posting, dealer-button rotation, or cross-hand chip persistence yet — every `Round` is
  fully independent, and stacks reset to the default each hand. Planned as Milestone 4.5.
- `poker_engine/bot.py`'s raise-sizing logic has a known bug: the raise amount is currently
  computed independently of `amount_to_call`, so it can be smaller than what's needed to even
  call a large bet. See the file for details.
