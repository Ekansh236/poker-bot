import contextlib
import pickle

import redis

from poker_engine.cards import Deck
from poker_engine.round import Round
from poker_engine.seat import Seat

SEATS_PER_TABLE = 2
LOCK_TIMEOUT_SECONDS = 10  # safety valve -- auto-releases if a worker crashes mid-lock
BOT_PLAYER_ID = "bot"

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


def seat_bot_if_needed(round_: Round) -> None:
    """Auto-fill any still-empty seat with a bot.

    Simplest possible matchmaking for a heads-up-only table: once a human
    claims one seat, whatever's left over becomes a bot immediately, so
    every table is always playable with no separate lobby/invite flow.
    """
    for seat in round_.seats:
        if seat.player is None:
            seat.player = BOT_PLAYER_ID
            seat.is_bot = True


@contextlib.contextmanager
def locked_round(table_id: str):
    """Safe read-modify-write access to a table's shared Round state.

    Acquires a Redis-backed lock scoped to this table, loads (or creates)
    the Round, yields it to the caller, then persists whatever the caller
    mutated and releases the lock -- even if the caller raised.
    """
    lock = redis_client.lock(f"lock:table:{table_id}", timeout=LOCK_TIMEOUT_SECONDS)
    with lock:
        pickled_round = redis_client.get(f"round:{table_id}")
        round_ = pickle.loads(pickled_round) if pickled_round else _new_round()
        try:
            yield round_
        finally:
            redis_client.set(f"round:{table_id}", pickle.dumps(round_))
