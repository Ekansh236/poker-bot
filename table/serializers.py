from poker_engine.round import Round


def serialize_round(round_: Round) -> dict:
    """Build the JSON-safe, opponent-safe state broadcast to the whole table."""
    # TODO(human): build and return a dict describing the table's current
    # public state -- pot, current turn, community cards, and each seat's
    # public info (stack, folded/all-in status, bet this street).
    #
    # Do NOT include seat.cards for anyone here. Hole cards are private --
    # delivering them to only the right player is a separate concern we'll
    # handle later, not part of this shared broadcast.
    json_safe_state = {
        "pot": round_.pot,
        "round_state": round_.current_round_state.name,
        "community_cards": [card.to_dict() for card in round_.community_cards],
        "current_bet_to_match": round_.current_bet_to_match,
        "current_turn": round_.seats[round_.current_turn_index].player if round_.seats else None,
        "seats": [
            {
                "player": seat.player,
                "stack": seat.stack,
                "is_folded": seat.is_folded,
                "is_all_in": seat.is_all_in,
                "bet_this_street": seat.bet_this_street,
                "total_contributed_to_pot": seat.total_contributed_to_pot,
            }
            for seat in round_.seats
        ],
    }
    return json_safe_state
