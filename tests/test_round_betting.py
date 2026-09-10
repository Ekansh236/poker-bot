import pytest

from poker_engine.cards import Deck
from poker_engine.round import Round
from poker_engine.seat import Seat


def make_round(num_seats=3):
    deck = Deck()
    deck.shuffle()
    seats = [Seat(f"P{i}", None) for i in range(num_seats)]
    round_ = Round(seats, deck)
    round_.deal_hole_cards()
    return round_, seats


def test_acting_out_of_turn_raises():
    round_, seats = make_round()
    with pytest.raises(ValueError):
        round_.apply_action(seats[1], "check")  # seat 0 acts first


def test_check_around_completes_betting_round():
    round_, seats = make_round()
    for seat in seats:
        round_.apply_action(seat, "check")
    assert round_.is_betting_round_complete()


def test_cannot_check_facing_a_bet():
    round_, seats = make_round(2)
    round_.apply_action(seats[0], "raise", 50)
    with pytest.raises(ValueError):
        round_.apply_action(seats[1], "check")


def test_call_matches_current_bet_and_moves_chips():
    round_, seats = make_round(2)
    round_.apply_action(seats[0], "raise", 50)
    round_.apply_action(seats[1], "call")
    assert seats[1].bet_this_street == 50
    assert seats[1].stack == 450
    assert round_.pot == 100


def test_raise_must_exceed_current_bet_to_match():
    round_, seats = make_round(2)
    round_.apply_action(seats[0], "raise", 50)
    with pytest.raises(ValueError):
        round_.apply_action(seats[1], "raise", 30)  # doesn't even match, let alone raise


def test_raise_reopens_action_for_players_who_already_acted():
    round_, seats = make_round(3)
    round_.apply_action(seats[0], "check")
    round_.apply_action(seats[1], "raise", 50)
    assert seats[0].has_acted_this_street is False  # reopened
    assert seats[2].has_acted_this_street is False


def test_fold_removes_seat_from_active_play():
    round_, seats = make_round(2)
    round_.apply_action(seats[0], "fold")
    assert seats[0].is_folded
    assert round_.check_if_all_but_one_folded()


def test_betting_round_not_complete_until_bets_match():
    round_, seats = make_round(2)
    round_.apply_action(seats[0], "raise", 50)
    assert not round_.is_betting_round_complete()
    round_.apply_action(seats[1], "call")
    assert round_.is_betting_round_complete()


def test_invalid_action_name_raises():
    round_, seats = make_round(2)
    with pytest.raises(ValueError):
        round_.apply_action(seats[0], "bogus_action")


def test_turn_advances_past_folded_and_all_in_seats():
    round_, seats = make_round(3)
    round_.apply_action(seats[0], "fold")
    # seats[1] should be next to act, not seats[0] again
    assert round_.seats[round_.current_turn_index] == seats[1]
