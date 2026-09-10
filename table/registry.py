import contextlib
import pickle

import redis

from poker_engine.cards import Deck
from poker_engine.round import Round
from poker_engine.seat import Seat

SEATS_PER_TABLE = 2
LOCK_TIMEOUT_SECONDS = 10  # safety valve -- auto-releases if a worker crashes mid-lock

# Same host/port as CHANNEL_LAYERS in settings.py -- one Redis instance backs
# both the pub/sub channel layer and this shared game-state store.
redis_client = redis.Redis(host='127.0.0.1', port=6379, db=0)


def _new_round() -> Round:
    deck = Deck()
    deck.shuffle()
    seats = [Seat(None, None) for _ in range(SEATS_PER_TABLE)]
    return Round(seats, deck)


def claim_seat(round_: Round, player_id: str) -> Seat:
    for seat in round_.seats:
        if seat.player == player_id:
            return seat
    for seat in round_.seats:
        if seat.player is None:
            seat.player = player_id
            return seat
    raise ValueError(f"Table is full -- no open seat for {player_id}.")


# TODO(human): implement locked_round(table_id) as a context manager.
#
# This replaces the old get_round() -- instead of just handing back a Round
# object (the exact lost-update bug we diagrammed: two workers reading the
# same stale state and one overwriting the other's write), it must:
#
#   1. Acquire a Redis-backed lock scoped to this table_id. redis-py gives
#      you this for free: redis_client.lock(name, timeout=LOCK_TIMEOUT_SECONDS)
#      returns an object that is ITSELF a context manager (supports `with`).
#      Pick a lock key name that's clearly table-scoped, e.g. f"lock:table:{table_id}".
#
#   2. While holding the lock, GET the pickled Round from Redis (key it by
#      table_id, e.g. f"round:{table_id}") and unpickle it with pickle.loads.
#      If nothing's stored yet (GET returns None), build a fresh one with
#      _new_round() instead.
#
#   3. yield that Round object out -- this is what makes
#      `with registry.locked_round(table_id) as round_:` work for callers.
#
#   4. After the caller's `with` block finishes -- whether it completed
#      normally or raised -- pickle the (possibly mutated) Round with
#      pickle.dumps and SET it back into Redis, THEN release the lock.
#      Use try/finally so the lock always releases even on an exception.
#
# You'll want the @contextlib.contextmanager decorator (already imported
# above) to write this as a generator function rather than a full class.
@contextlib.contextmanager
def locked_round(table_id: str):
    lock = redis_client.lock(f"lock:table:{table_id}", timeout=LOCK_TIMEOUT_SECONDS)
    with lock:
        pickled_round = redis_client.get(f"round:{table_id}")
        round_ = pickle.loads(pickled_round) if pickled_round else _new_round()
        try:
            yield round_
        finally:
            redis_client.set(f"round:{table_id}", pickle.dumps(round_))
