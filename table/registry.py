from poker_engine.cards import Deck
from poker_engine.round import Round
from poker_engine.seat import Seat

# Process-local only -- a stand-in until real shared storage (Redis) is
# designed in a later sub-step. Fine for single-process local testing.
TABLES: dict[str, Round] = {}

SEATS_PER_TABLE = 2


def get_round(table_id: str) -> Round:
    if table_id not in TABLES:
        deck = Deck()
        deck.shuffle()
        seats = [Seat(None, None) for _ in range(SEATS_PER_TABLE)]
        TABLES[table_id] = Round(seats, deck)
    return TABLES[table_id]


def claim_seat(round_: Round, player_id: str) -> Seat:
    for seat in round_.seats:
        if seat.player == player_id:
            return seat
    for seat in round_.seats:
        if seat.player is None:
            seat.player = player_id
            return seat
    raise ValueError(f"Table is full -- no open seat for {player_id}.")
