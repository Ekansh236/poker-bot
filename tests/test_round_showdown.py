from poker_engine.cards import Card, Deck, Rank, Suit
from poker_engine.round import Round
from poker_engine.seat import Seat


def make_round(num_seats):
    return Round([Seat(f"P{i}", None) for i in range(num_seats)], Deck())


def test_fold_win_awards_entire_pot_to_last_player():
    round_ = make_round(2)
    a, b = round_.seats
    a.total_contributed_to_pot = 200
    b.total_contributed_to_pot = 200
    b.is_folded = True
    round_.pot = 400

    results = round_.showdown_resolution()

    assert results == [(a, 400)]
    assert a.stack == 900  # started at 500, +400 won


def test_heads_up_showdown_best_hand_wins():
    round_ = make_round(2)
    a, b = round_.seats
    a.cards = (Card(Rank.ACE, Suit.HEARTS), Card(Rank.ACE, Suit.SPADES))
    b.cards = (Card(Rank.TWO, Suit.CLUBS), Card(Rank.THREE, Suit.DIAMONDS))
    a.stack = 400  # already put 100 in, mirroring what put_in_pot() would've done
    b.stack = 400
    a.total_contributed_to_pot = 100
    b.total_contributed_to_pot = 100
    round_.pot = 200
    round_.community_cards = [
        Card(Rank.KING, Suit.HEARTS), Card(Rank.QUEEN, Suit.CLUBS), Card(Rank.JACK, Suit.SPADES),
        Card(Rank.FOUR, Suit.HEARTS), Card(Rank.NINE, Suit.DIAMONDS),
    ]

    results = round_.showdown_resolution()

    assert results == [(a, 200)]
    assert a.stack == 600  # 400 remaining + 200 won
    assert b.stack == 400  # lost the 100 they put in, wins nothing


def test_showdown_splits_tie_evenly():
    round_ = make_round(2)
    a, b = round_.seats
    # Both play the same board -- identical hand strength.
    a.cards = (Card(Rank.TWO, Suit.CLUBS), Card(Rank.THREE, Suit.DIAMONDS))
    b.cards = (Card(Rank.TWO, Suit.SPADES), Card(Rank.THREE, Suit.HEARTS))
    a.total_contributed_to_pot = 100
    b.total_contributed_to_pot = 100
    round_.pot = 200
    round_.community_cards = [
        Card(Rank.KING, Suit.HEARTS), Card(Rank.QUEEN, Suit.CLUBS), Card(Rank.JACK, Suit.SPADES),
        Card(Rank.NINE, Suit.HEARTS), Card(Rank.EIGHT, Suit.DIAMONDS),
    ]

    results = round_.showdown_resolution()

    amounts = {seat.player: amount for seat, amount in results}
    assert amounts == {"P0": 100, "P1": 100}


def test_side_pot_showdown_awards_different_pots_to_different_winners():
    round_ = make_round(3)
    a, b, c = round_.seats
    a.cards = (Card(Rank.ACE, Suit.HEARTS), Card(Rank.ACE, Suit.SPADES))     # best hand, short stack
    b.cards = (Card(Rank.KING, Suit.HEARTS), Card(Rank.KING, Suit.CLUBS))    # ties C on the side pot
    c.cards = (Card(Rank.KING, Suit.DIAMONDS), Card(Rank.KING, Suit.SPADES))
    a.total_contributed_to_pot = 50
    b.total_contributed_to_pot = 500
    c.total_contributed_to_pot = 500
    round_.pot = 1050
    round_.community_cards = [
        Card(Rank.TWO, Suit.HEARTS), Card(Rank.SEVEN, Suit.CLUBS), Card(Rank.NINE, Suit.SPADES),
        Card(Rank.FOUR, Suit.HEARTS), Card(Rank.SIX, Suit.DIAMONDS),
    ]

    results = round_.showdown_resolution()

    amounts = {seat.player: amount for seat, amount in results}
    assert amounts["P0"] == 150   # main pot only: 50 * 3 contributors
    assert amounts["P1"] == 450   # side pot split with C
    assert amounts["P2"] == 450
    assert sum(amounts.values()) == 1050


def test_pot_layer_with_no_eligible_seats_refunds_its_contributors():
    # A and B both contributed up to the 500 level, matching each other, then
    # both folded -- nobody active is eligible to win that layer. Rather than
    # crashing (the original bug), it should refund that layer evenly back to
    # whoever paid into it, folded or not.
    round_ = make_round(4)
    a, b, c, d = round_.seats
    c.cards = (Card(Rank.TWO, Suit.CLUBS), Card(Rank.THREE, Suit.DIAMONDS))
    d.cards = (Card(Rank.FOUR, Suit.CLUBS), Card(Rank.FIVE, Suit.DIAMONDS))
    round_.community_cards = [
        Card(Rank.SIX, Suit.HEARTS), Card(Rank.SEVEN, Suit.SPADES), Card(Rank.NINE, Suit.CLUBS),
        Card(Rank.JACK, Suit.HEARTS), Card(Rank.KING, Suit.DIAMONDS),
    ]
    a.total_contributed_to_pot = 500
    b.total_contributed_to_pot = 500
    a.is_folded = True
    b.is_folded = True
    c.total_contributed_to_pot = 100
    d.total_contributed_to_pot = 100
    round_.pot = 1200

    results = round_.showdown_resolution()

    amounts = {seat.player: amount for seat, amount in results}
    assert amounts["P0"] == 400  # orphaned layer (100->500) refunded evenly to A and B
    assert amounts["P1"] == 400
    # main layer (0->100) is funded by all 4 seats (400 total) and C/D tie for
    # it, so they split it evenly -- still resolved normally, not refunded.
    assert amounts["P2"] == 200
    assert amounts["P3"] == 200
    assert sum(amounts.values()) == 1200
