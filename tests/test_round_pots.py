from poker_engine.cards import Deck
from poker_engine.round import Round
from poker_engine.seat import Seat


def make_round(num_seats):
    return Round([Seat(f"P{i}", None) for i in range(num_seats)], Deck())


def test_compute_pots_single_pot_when_no_all_ins():
    round_ = make_round(2)
    for seat in round_.seats:
        seat.total_contributed_to_pot = 100
    pots = round_.compute_pots()
    assert pots == [(200, round_.seats, round_.seats)]


def test_compute_pots_creates_side_pot_layers():
    round_ = make_round(4)
    a, b, c, d = round_.seats
    a.total_contributed_to_pot = 50
    b.total_contributed_to_pot = 150
    c.total_contributed_to_pot = 500
    d.total_contributed_to_pot = 500

    pots = round_.compute_pots()

    assert [amount for amount, _, _ in pots] == [200, 300, 700]
    assert sum(amount for amount, _, _ in pots) == 1200
    assert {seat.player for seat in pots[0][1]} == {"P0", "P1", "P2", "P3"}
    assert {seat.player for seat in pots[1][1]} == {"P1", "P2", "P3"}
    assert {seat.player for seat in pots[2][1]} == {"P2", "P3"}


def test_compute_pots_excludes_folded_seats_from_eligibility_but_not_amount():
    round_ = make_round(3)
    a, b, c = round_.seats
    a.total_contributed_to_pot = 50
    a.is_folded = True
    b.total_contributed_to_pot = 500
    c.total_contributed_to_pot = 500

    pots = round_.compute_pots()

    total = sum(amount for amount, _, _ in pots)
    assert total == 1050  # A's folded chips still count toward the pot
    assert all("P0" not in {s.player for s in eligible} for _, eligible, _ in pots)
    # But A still shows up as a CONTRIBUTOR to the first layer -- that's what
    # lets an orphaned layer (nobody eligible) get refunded to the right seats.
    assert "P0" in {s.player for s in pots[0][2]}


def test_refund_uncalled_bets_no_op_when_tied():
    round_ = make_round(2)
    a, b = round_.seats
    a.total_contributed_to_pot = 500
    b.total_contributed_to_pot = 500
    round_.pot = 1000
    round_.refund_uncalled_bets()
    assert a.total_contributed_to_pot == 500
    assert a.stack == 500
    assert round_.pot == 1000


def test_refund_uncalled_bets_returns_excess_to_stack_and_pot():
    round_ = make_round(2)
    a, b = round_.seats
    a.stack = 200  # pretend A already put 300 in from a 500 starting stack
    a.total_contributed_to_pot = 300
    b.total_contributed_to_pot = 100
    round_.pot = 400

    round_.refund_uncalled_bets()

    assert a.stack == 400  # got the uncalled 200 back
    assert a.total_contributed_to_pot == 100
    assert round_.pot == 200  # pot shrinks by the same refunded amount


def test_refund_uncalled_bets_skips_folded_top_contributor():
    round_ = make_round(2)
    a, b = round_.seats
    a.total_contributed_to_pot = 300
    a.is_folded = True
    b.total_contributed_to_pot = 100
    round_.pot = 400

    round_.refund_uncalled_bets()

    # A folded -- their excess stays in the pot rather than being refunded.
    assert a.total_contributed_to_pot == 300
    assert round_.pot == 400
