"""Specs for the elimination TODO(human) in Round._resolve_showdown_and_start_new_hand().

At 2 seats, busting IS losing -- these tests are all about 3+ seats, where
busting one seat must NOT end the game for everyone else, and the busted
seat must stay excluded from every hand after the one that busted it.
"""

from poker_engine.cards import Card, Deck, Rank, Suit
from poker_engine.round import Round
from poker_engine.seat import Seat


def make_round(num_seats):
    return Round([Seat(f"P{i}", None) for i in range(num_seats)], Deck())


def test_bust_with_three_seats_does_not_end_the_game():
    round_ = make_round(3)
    a, b, c = round_.seats
    c.is_folded = True  # sitting out this hand, uninvolved either way

    # A real showdown between A and B, A has the clear best hand -- B
    # already put its entire stack in earlier in this same hand (all-in),
    # so losing leaves B at exactly 0.
    a.cards = (Card(Rank.ACE, Suit.HEARTS), Card(Rank.ACE, Suit.SPADES))
    b.cards = (Card(Rank.TWO, Suit.CLUBS), Card(Rank.THREE, Suit.DIAMONDS))
    a.stack = 400
    a.total_contributed_to_pot = 100
    b.stack = 0
    b.is_all_in = True
    b.total_contributed_to_pot = 100
    round_.pot = 200
    round_.community_cards = [
        Card(Rank.KING, Suit.HEARTS), Card(Rank.QUEEN, Suit.CLUBS), Card(Rank.JACK, Suit.SPADES),
        Card(Rank.FOUR, Suit.HEARTS), Card(Rank.NINE, Suit.DIAMONDS),
    ]

    round_._resolve_showdown_and_start_new_hand()

    # Two seats (A and C) still have chips -- busting B alone must not end it.
    # NOTE: can't assert a.stack == 600 here -- when the game continues,
    # this method also immediately deals and blinds the NEXT hand (same
    # contract as before this feature existed), so A's stack moves again
    # based on whatever it's dealt into next. That's covered separately by
    # test_busted_seat_posts_no_blind_and_never_acts.
    assert round_.game_over is False
    assert b.stack == 0


def test_busted_seat_gets_no_cards_in_the_next_hand():
    round_ = make_round(3)
    a, b, c = round_.seats
    c.is_folded = True
    a.cards = (Card(Rank.ACE, Suit.HEARTS), Card(Rank.ACE, Suit.SPADES))
    b.cards = (Card(Rank.TWO, Suit.CLUBS), Card(Rank.THREE, Suit.DIAMONDS))
    a.stack, a.total_contributed_to_pot = 400, 100
    b.stack, b.is_all_in, b.total_contributed_to_pot = 0, True, 100
    round_.pot = 200
    round_.community_cards = [
        Card(Rank.KING, Suit.HEARTS), Card(Rank.QUEEN, Suit.CLUBS), Card(Rank.JACK, Suit.SPADES),
        Card(Rank.FOUR, Suit.HEARTS), Card(Rank.NINE, Suit.DIAMONDS),
    ]

    round_._resolve_showdown_and_start_new_hand()

    # start_new_hand() dealt a fresh hand to whoever's still in -- B should
    # not be one of them.
    assert not b.cards
    assert a.cards
    assert c.cards


def test_busted_seat_posts_no_blind_and_never_acts():
    round_ = make_round(3)
    a, b, c = round_.seats
    c.is_folded = True
    a.cards = (Card(Rank.ACE, Suit.HEARTS), Card(Rank.ACE, Suit.SPADES))
    b.cards = (Card(Rank.TWO, Suit.CLUBS), Card(Rank.THREE, Suit.DIAMONDS))
    a.stack, a.total_contributed_to_pot = 400, 100
    b.stack, b.is_all_in, b.total_contributed_to_pot = 0, True, 100
    round_.pot = 200
    round_.community_cards = [
        Card(Rank.KING, Suit.HEARTS), Card(Rank.QUEEN, Suit.CLUBS), Card(Rank.JACK, Suit.SPADES),
        Card(Rank.FOUR, Suit.HEARTS), Card(Rank.NINE, Suit.DIAMONDS),
    ]

    round_._resolve_showdown_and_start_new_hand()

    # B stays at exactly 0 -- a blind posted from/by a busted seat would
    # move this number.
    assert b.stack == 0
    assert round_.seats[round_.current_turn_index] is not b
    assert round_.seats[round_.button_index] is not b


def test_game_ends_once_only_one_seat_has_chips_left():
    round_ = make_round(3)
    a, b, c = round_.seats
    # C busted out in some earlier hand -- already at 0, sitting out.
    c.stack = 0
    c.is_folded = True
    c.cards = None

    # This hand's showdown between A and B leaves B at 0 too -- only A
    # has chips left anywhere at the table once this resolves.
    a.cards = (Card(Rank.ACE, Suit.HEARTS), Card(Rank.ACE, Suit.SPADES))
    b.cards = (Card(Rank.TWO, Suit.CLUBS), Card(Rank.THREE, Suit.DIAMONDS))
    a.stack, a.total_contributed_to_pot = 400, 100
    b.stack, b.is_all_in, b.total_contributed_to_pot = 0, True, 100
    round_.pot = 200
    round_.community_cards = [
        Card(Rank.KING, Suit.HEARTS), Card(Rank.QUEEN, Suit.CLUBS), Card(Rank.JACK, Suit.SPADES),
        Card(Rank.FOUR, Suit.HEARTS), Card(Rank.NINE, Suit.DIAMONDS),
    ]

    round_._resolve_showdown_and_start_new_hand()

    assert round_.game_over is True
    assert round_.pot == 0
