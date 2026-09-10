from poker_engine.seat import Seat


def test_new_seat_defaults():
    seat = Seat("Alice", None)
    assert seat.stack == 500
    assert seat.bet_this_street == 0
    assert seat.total_contributed_to_pot == 0
    assert not seat.is_folded
    assert not seat.is_all_in


def test_put_in_pot_moves_chips():
    seat = Seat("Alice", None)
    actual = seat.put_in_pot(100)
    assert actual == 100
    assert seat.stack == 400
    assert seat.bet_this_street == 100
    assert seat.total_contributed_to_pot == 100


def test_put_in_pot_clamps_to_available_stack():
    seat = Seat("Alice", None)
    actual = seat.put_in_pot(9999)
    assert actual == 500
    assert seat.stack == 0
    assert seat.is_all_in


def test_put_in_pot_accumulates_across_multiple_calls():
    seat = Seat("Alice", None)
    seat.put_in_pot(100)
    seat.put_in_pot(50)
    assert seat.bet_this_street == 150
    assert seat.total_contributed_to_pot == 150
    assert seat.stack == 350


def test_fold_sets_flag():
    seat = Seat("Alice", None)
    seat.fold()
    assert seat.is_folded


def test_reset_for_new_hand_clears_per_hand_state():
    seat = Seat("Alice", None)
    seat.put_in_pot(200)
    seat.fold()
    seat.reset_for_new_hand()
    assert seat.bet_this_street == 0
    assert seat.total_contributed_to_pot == 0
    assert not seat.is_folded
    assert not seat.is_all_in
    # Stack is NOT a per-hand field -- winnings/losses must carry over.
    assert seat.stack == 300
