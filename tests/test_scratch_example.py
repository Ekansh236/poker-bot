from poker_engine.cards import Deck
from poker_engine.round import Round, RoundState
from poker_engine.seat import Seat


def test_new_seat_starts_with_default_stack():
    seat = Seat("alice", None)
    assert seat.stack == 500


def play_checked_out_street(round_):
    """Have both seats check/call their way through the current street --
    acting on round_.current_turn_index each time, not a fixed seat order,
    since who acts first flips between preflop (button) and postflop (the
    non-button seat). The button also owes a call preflop (blinds leave a
    bet to match), so a bare "check" for both seats only works postflop.
    """
    for _ in range(len(round_.seats)):
        seat = round_.seats[round_.current_turn_index]
        amount_to_call = round_.current_bet_to_match - seat.bet_this_street
        round_.apply_action(seat, "call" if amount_to_call > 0 else "check")


def play_checked_out_hand():
    """Deal a heads-up hand and check/call it all the way to showdown."""
    seats = [Seat("alice", None), Seat("bob", None)]
    round_ = Round(seats, Deck())

    round_.deal_hole_cards()
    play_checked_out_street(round_)

    round_.flop_community_cards()
    play_checked_out_street(round_)

    round_.turn_community_card()
    play_checked_out_street(round_)

    round_.river_community_card()
    play_checked_out_street(round_)

    return round_


def test_playing_through_a_few_hands_in_a_row():
    for _ in range(3):
        round_ = play_checked_out_hand()

        assert round_.current_round_state == RoundState.SHOWDOWN
        assert len(round_.community_cards) == 5

        results = round_.showdown_resolution()
        total_awarded = sum(amount for _, amount in results)
        assert total_awarded == round_.pot


def test_a_hand_that_ends_early_by_fold():
    seats = [Seat("alice", None), Seat("bob", None)]
    round_ = Round(seats, Deck())
    round_.deal_hole_cards()

    round_.apply_action(seats[0], "fold")

    assert round_.check_if_all_but_one_folded()
    results = round_.showdown_resolution()
    assert results == [(seats[1], round_.pot)]
