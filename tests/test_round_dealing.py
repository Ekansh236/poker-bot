import pytest

from poker_engine.cards import Deck
from poker_engine.round import Round, RoundState
from poker_engine.seat import Seat


def make_round(num_seats=3):
    deck = Deck()
    deck.shuffle()
    seats = [Seat(f"P{i}", None) for i in range(num_seats)]
    return Round(seats, deck), seats


def test_deal_hole_cards_gives_each_seat_two_unique_cards():
    round_, seats = make_round()
    round_.deal_hole_cards()
    dealt = []
    for seat in seats:
        assert len(seat.cards) == 2
        dealt.extend(seat.cards)
    assert len(set(dealt)) == len(dealt)


def test_deal_hole_cards_transitions_to_flop_state():
    round_, _ = make_round()
    round_.deal_hole_cards()
    assert round_.current_round_state == RoundState.FLOP


def test_deal_hole_cards_rejects_wrong_state():
    round_, _ = make_round()
    round_.deal_hole_cards()
    with pytest.raises(ValueError):
        round_.deal_hole_cards()


def test_flop_deals_three_cards_and_burns_one():
    round_, _ = make_round()
    round_.deal_hole_cards()
    deck_size_before = len(round_.deck.cards)
    flop = round_.flop_community_cards()
    assert len(flop) == 3
    assert len(round_.community_cards) == 3
    assert len(round_.deck.cards) == deck_size_before - 4  # 1 burn + 3 dealt
    assert round_.current_round_state == RoundState.TURN


def test_turn_deals_one_card_and_burns_one():
    round_, _ = make_round()
    round_.deal_hole_cards()
    round_.flop_community_cards()
    deck_size_before = len(round_.deck.cards)
    round_.turn_community_card()
    assert len(round_.community_cards) == 4
    assert len(round_.deck.cards) == deck_size_before - 2  # 1 burn + 1 dealt
    assert round_.current_round_state == RoundState.RIVER


def test_river_deals_one_card_and_transitions_to_showdown():
    round_, _ = make_round()
    round_.deal_hole_cards()
    round_.flop_community_cards()
    round_.turn_community_card()
    round_.river_community_card()
    assert len(round_.community_cards) == 5
    assert round_.current_round_state == RoundState.SHOWDOWN


def test_flop_rejects_wrong_state():
    round_, _ = make_round()
    with pytest.raises(ValueError):
        round_.flop_community_cards()  # still PRE_FLOP, hole cards not dealt yet


def test_bet_this_street_resets_between_streets():
    round_, seats = make_round(2)
    round_.deal_hole_cards()
    round_.apply_action(seats[0], "check")
    round_.apply_action(seats[1], "raise", 50)
    round_.apply_action(seats[0], "call")
    assert seats[1].bet_this_street == 50
    round_.flop_community_cards()
    assert all(seat.bet_this_street == 0 for seat in seats)
    # total_contributed_to_pot must NOT reset mid-hand -- only bet_this_street does.
    assert seats[1].total_contributed_to_pot == 50
