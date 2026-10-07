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


def test_real_showdown_with_a_busted_seat_still_at_the_table():
    # C busted out in some earlier hand -- permanently is_all_in, cards
    # None, not is_folded (see start_new_hand()'s reset guard). A and B
    # now play this hand out to a REAL showdown (both call it down, both
    # still holding cards) -- this used to crash building the revealed
    # hands dict, since "not is_folded" alone still counted C as live.
    round_ = make_round(3)
    a, b, c = round_.seats
    c.stack = 0
    c.is_all_in = True
    c.cards = None

    a.cards = (Card(Rank.ACE, Suit.HEARTS), Card(Rank.ACE, Suit.SPADES))
    b.cards = (Card(Rank.TWO, Suit.CLUBS), Card(Rank.THREE, Suit.DIAMONDS))
    a.total_contributed_to_pot = 100
    b.total_contributed_to_pot = 100
    round_.pot = 200
    round_.community_cards = [
        Card(Rank.KING, Suit.HEARTS), Card(Rank.QUEEN, Suit.CLUBS), Card(Rank.JACK, Suit.SPADES),
        Card(Rank.FOUR, Suit.HEARTS), Card(Rank.NINE, Suit.DIAMONDS),
    ]

    round_._resolve_showdown_and_start_new_hand()  # must not raise

    assert "P2" not in round_.last_showdown["hands"]
    assert "P0" in round_.last_showdown["hands"]
    assert "P1" in round_.last_showdown["hands"]


def test_busted_seat_contribution_tally_resets_each_hand():
    # B busts this hand with a real contribution already on the books --
    # start_new_hand() must not leave that stale total_contributed_to_pot
    # sitting there forever, or compute_pots() keeps treating B as a real
    # contributor in every future hand (see the showdown test above for
    # what that crashes into).
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

    assert b.total_contributed_to_pot == 0
    assert b.bet_this_street == 0
    assert b.is_all_in is True


def test_seat_going_all_in_on_the_blind_itself_still_gets_dealt_in():
    # B has fewer chips than the small blind -- put_in_pot() caps the post
    # at B's whole stack, landing B at exactly 0 by the time dealing
    # happens. B still contributed everything it had THIS hand and is a
    # real participant, not an already-busted seat from a prior hand --
    # it must still get cards.
    round_ = make_round(3)
    a, b, c = round_.seats
    b.stack = 3  # less than SMALL_BLIND (5)
    round_.button_index = 0  # a is the button -- b (next active) posts the small blind

    round_.deal_hole_cards()

    assert b.stack == 0
    assert b.cards is not None
    assert b.total_contributed_to_pot == 3


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


def test_last_live_opponent_folding_is_recognized_as_a_fold_win_despite_a_busted_seat():
    # C busted out in some earlier hand (permanently is_all_in, cards=None,
    # never is_folded -- see start_new_hand()'s reset guard). This hand, B
    # (the only other real opponent) folds to A -- that must immediately
    # end the hand in A's favor, not get missed because C still silently
    # counts as "active" to a naive `not seat.is_folded` check.
    round_ = make_round(3)
    a, b, c = round_.seats
    c.stack = 0
    c.is_all_in = True
    c.cards = None
    a.cards = (Card(Rank.ACE, Suit.HEARTS), Card(Rank.ACE, Suit.SPADES))
    b.cards = (Card(Rank.TWO, Suit.CLUBS), Card(Rank.THREE, Suit.DIAMONDS))
    round_.current_turn_index = round_.seats.index(b)
    round_.pot = 20
    a.total_contributed_to_pot = 10
    b.total_contributed_to_pot = 10
    a.bet_this_street = 10
    a.has_acted_this_street = True

    round_.apply_action_and_advance(seat=b, action="fold", amount=0)

    # Confirms the pot was actually awarded to A, not lost or handed to C --
    # NOTE: can't assert a.stack directly here, since this also immediately
    # deals and blinds the next hand (same contract as every other
    # fold-win/showdown resolution), which moves A's stack again right
    # after. See test_fold_win_pot_goes_to_the_real_winner_not_a_busted_seat_sitting_earlier
    # for the direct pot-award assertion in isolation.
    assert round_.last_showdown["results"] == [{"player": "P0", "amount": 20}]


def test_fold_win_pot_goes_to_the_real_winner_not_a_busted_seat_sitting_earlier():
    # The busted seat (A) sits BEFORE the real winner (B) in seat order --
    # a naive `next(seat for seat in self.seats if not seat.is_folded)`
    # picks A first, since A is never actually marked is_folded, and hands
    # the whole pot to a seat that's already out of the game.
    round_ = make_round(3)
    a, b, c = round_.seats
    a.stack = 0
    a.is_all_in = True
    a.cards = None
    b.cards = (Card(Rank.ACE, Suit.HEARTS), Card(Rank.ACE, Suit.SPADES))
    c.is_folded = True
    round_.pot = 100
    b.total_contributed_to_pot = 100

    results = round_.showdown_resolution()

    assert results == [(b, 100)]
    assert b.stack == 600  # started at 500, +100 won
    assert a.stack == 0  # must NOT have received the pot
