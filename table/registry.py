import contextlib
import pickle

import redis

from poker_engine.cards import Deck
from poker_engine.round import Round
from poker_engine.seat import Seat

SEATS_PER_TABLE = 5
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
    # Before a hand is dealt, every open seat still gets bot-filled
    # immediately on the FIRST connection (see seat_bot_if_needed) so a
    # lone player can start right away -- which otherwise leaves no room
    # for a second real player to ever join afterward. Safe to bump a bot
    # back out only while nothing's been dealt yet; once cards are out,
    # a bot's stack/position is live game state, not a placeholder.
    if all(seat.cards is None for seat in round_.seats):
        for seat in round_.seats:
            if seat.is_bot:
                seat.player = player_id
                seat.is_bot = False
                return seat
    raise ValueError(f"Table is full -- no open seat for {player_id}.")


def seat_bot_if_needed(round_: Round) -> None:
    """Auto-fill every still-empty seat with a bot.

    Simplest possible matchmaking: once a human claims one seat, whatever's
    left over becomes bots immediately, so every table is always playable
    with no separate lobby/invite flow. Each bot gets a name unique to its
    seat index -- claim_seat() resolves a player_id to the first seat whose
    .player matches, so every bot sharing the same literal "bot" name (fine
    when at most one existed, at the old 2-seat table cap) would make every
    bot_decide_task() call for seat 2+ silently resolve back to seat 1.
    """
    for index, seat in enumerate(round_.seats):
        if seat.player is None:
            seat.player = f"{BOT_PLAYER_ID}{index}"
            seat.is_bot = True


def all_table_ids() -> list[str]:
    """Every table_id with a live Round currently stored in Redis."""
    return [key.decode().removeprefix("round:") for key in redis_client.scan_iter("round:*")]


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
