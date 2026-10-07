from poker_engine.bot import bot_decide
from poker_engine.cards import Card, Deck, Rank, Suit
from poker_engine.round import Round
from poker_engine.seat import Seat


def test_bot_decide_does_not_count_busted_seats_as_opponents(monkeypatch):
    # 9-seat table, but 6 of them already busted out in earlier hands --
    # only P0 (the bot deciding) and two others (P7, P8) are still really
    # playing. bot_decide() must simulate equity against 2 real opponents,
    # not 8 (6 busted ghosts + the 2 real ones).
    seats = [Seat(f"P{i}", None) for i in range(9)]
    round_ = Round(seats, Deck())
    bot_seat = seats[0]
    for s in seats[1:7]:
        s.stack, s.is_all_in, s.cards = 0, True, None
    for s in seats[7:]:
        s.cards = (Card(Rank.TWO, Suit.CLUBS), Card(Rank.THREE, Suit.DIAMONDS))
    bot_seat.cards = (Card(Rank.ACE, Suit.HEARTS), Card(Rank.ACE, Suit.SPADES))
    round_.current_turn_index = 0
    round_.current_bet_to_match = 10
    round_.pot = 15

    seen_num_opponents = []
    import poker_engine.bot as bot_module
    real_estimate_equity = bot_module.estimate_equity

    def spy_estimate_equity(hole_cards, community_cards, num_opponents=1, num_trials=1000):
        seen_num_opponents.append(num_opponents)
        return real_estimate_equity(hole_cards, community_cards, num_opponents, num_trials)

    monkeypatch.setattr(bot_module, "estimate_equity", spy_estimate_equity)

    bot_decide(round_, bot_seat)

    assert seen_num_opponents == [2]
