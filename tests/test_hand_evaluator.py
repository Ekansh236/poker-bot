from poker_engine.cards import Card, Rank, Suit
from poker_engine.hand_evaluator import Hands, best_hand_from_seven, evaluate_hand


def cards(*rank_suit_pairs):
    return [Card(rank, suit) for rank, suit in rank_suit_pairs]


def test_high_card():
    hand = cards(
        (Rank.TWO, Suit.HEARTS), (Rank.FIVE, Suit.CLUBS), (Rank.NINE, Suit.DIAMONDS),
        (Rank.JACK, Suit.CLUBS), (Rank.ACE, Suit.HEARTS),
    )
    assert evaluate_hand(hand)[0] == Hands.HIGH_CARD


def test_one_pair():
    hand = cards(
        (Rank.TWO, Suit.HEARTS), (Rank.TWO, Suit.CLUBS), (Rank.FIVE, Suit.DIAMONDS),
        (Rank.NINE, Suit.CLUBS), (Rank.KING, Suit.HEARTS),
    )
    assert evaluate_hand(hand)[0] == Hands.ONE_PAIR


def test_two_pair():
    hand = cards(
        (Rank.TWO, Suit.HEARTS), (Rank.TWO, Suit.CLUBS), (Rank.FIVE, Suit.DIAMONDS),
        (Rank.FIVE, Suit.CLUBS), (Rank.KING, Suit.HEARTS),
    )
    assert evaluate_hand(hand)[0] == Hands.TWO_PAIR


def test_three_of_a_kind():
    hand = cards(
        (Rank.TWO, Suit.HEARTS), (Rank.TWO, Suit.CLUBS), (Rank.TWO, Suit.DIAMONDS),
        (Rank.FIVE, Suit.CLUBS), (Rank.KING, Suit.HEARTS),
    )
    assert evaluate_hand(hand)[0] == Hands.THREE_OF_A_KIND


def test_straight():
    hand = cards(
        (Rank.FIVE, Suit.HEARTS), (Rank.SIX, Suit.CLUBS), (Rank.SEVEN, Suit.DIAMONDS),
        (Rank.EIGHT, Suit.CLUBS), (Rank.NINE, Suit.HEARTS),
    )
    assert evaluate_hand(hand)[0] == Hands.STRAIGHT


def test_wheel_straight_ace_plays_low():
    hand = cards(
        (Rank.ACE, Suit.HEARTS), (Rank.TWO, Suit.CLUBS), (Rank.THREE, Suit.DIAMONDS),
        (Rank.FOUR, Suit.CLUBS), (Rank.FIVE, Suit.HEARTS),
    )
    result = evaluate_hand(hand)
    assert result[0] == Hands.STRAIGHT
    # Ace should rank LOWEST in the wheel, not highest.
    assert result[1][0] == Rank.FIVE
    assert result[1][-1] == Rank.ACE


def test_wheel_loses_to_six_high_straight():
    wheel = evaluate_hand(cards(
        (Rank.ACE, Suit.HEARTS), (Rank.TWO, Suit.CLUBS), (Rank.THREE, Suit.DIAMONDS),
        (Rank.FOUR, Suit.CLUBS), (Rank.FIVE, Suit.HEARTS),
    ))
    six_high = evaluate_hand(cards(
        (Rank.TWO, Suit.HEARTS), (Rank.THREE, Suit.CLUBS), (Rank.FOUR, Suit.DIAMONDS),
        (Rank.FIVE, Suit.CLUBS), (Rank.SIX, Suit.HEARTS),
    ))
    assert six_high > wheel


def test_flush():
    hand = cards(
        (Rank.TWO, Suit.HEARTS), (Rank.FIVE, Suit.HEARTS), (Rank.NINE, Suit.HEARTS),
        (Rank.JACK, Suit.HEARTS), (Rank.KING, Suit.HEARTS),
    )
    assert evaluate_hand(hand)[0] == Hands.FLUSH


def test_full_house():
    hand = cards(
        (Rank.TWO, Suit.HEARTS), (Rank.TWO, Suit.CLUBS), (Rank.TWO, Suit.DIAMONDS),
        (Rank.FIVE, Suit.CLUBS), (Rank.FIVE, Suit.HEARTS),
    )
    assert evaluate_hand(hand)[0] == Hands.FULL_HOUSE


def test_four_of_a_kind():
    hand = cards(
        (Rank.TWO, Suit.HEARTS), (Rank.TWO, Suit.CLUBS), (Rank.TWO, Suit.DIAMONDS),
        (Rank.TWO, Suit.SPADES), (Rank.FIVE, Suit.HEARTS),
    )
    assert evaluate_hand(hand)[0] == Hands.FOUR_OF_A_KIND


def test_straight_flush():
    hand = cards(
        (Rank.FIVE, Suit.HEARTS), (Rank.SIX, Suit.HEARTS), (Rank.SEVEN, Suit.HEARTS),
        (Rank.EIGHT, Suit.HEARTS), (Rank.NINE, Suit.HEARTS),
    )
    assert evaluate_hand(hand)[0] == Hands.STRAIGHT_FLUSH


def test_royal_flush():
    hand = cards(
        (Rank.TEN, Suit.HEARTS), (Rank.JACK, Suit.HEARTS), (Rank.QUEEN, Suit.HEARTS),
        (Rank.KING, Suit.HEARTS), (Rank.ACE, Suit.HEARTS),
    )
    assert evaluate_hand(hand)[0] == Hands.ROYAL_FLUSH


def test_ace_king_queen_jack_flush_without_ten_is_not_royal():
    # Four "royal" ranks plus a broken straight (9 instead of 10) -- should be
    # a plain flush, not a false-positive royal flush.
    hand = cards(
        (Rank.ACE, Suit.HEARTS), (Rank.KING, Suit.HEARTS), (Rank.QUEEN, Suit.HEARTS),
        (Rank.JACK, Suit.HEARTS), (Rank.NINE, Suit.HEARTS),
    )
    assert evaluate_hand(hand)[0] == Hands.FLUSH


def test_hand_category_ordering():
    high_card = evaluate_hand(cards(
        (Rank.TWO, Suit.HEARTS), (Rank.FIVE, Suit.CLUBS), (Rank.NINE, Suit.DIAMONDS),
        (Rank.JACK, Suit.CLUBS), (Rank.ACE, Suit.HEARTS),
    ))
    full_house = evaluate_hand(cards(
        (Rank.TWO, Suit.HEARTS), (Rank.TWO, Suit.CLUBS), (Rank.TWO, Suit.DIAMONDS),
        (Rank.FIVE, Suit.CLUBS), (Rank.FIVE, Suit.HEARTS),
    ))
    assert full_house > high_card


def test_best_hand_from_seven_picks_four_of_a_kind():
    seven_cards = cards(
        (Rank.ACE, Suit.HEARTS), (Rank.ACE, Suit.SPADES),          # hole cards
        (Rank.ACE, Suit.CLUBS), (Rank.ACE, Suit.DIAMONDS), (Rank.KING, Suit.HEARTS),
        (Rank.TWO, Suit.CLUBS), (Rank.SEVEN, Suit.DIAMONDS),        # board
    )
    best_five, hand_rank = best_hand_from_seven(seven_cards)
    assert hand_rank[0] == Hands.FOUR_OF_A_KIND
    assert len(best_five) == 5
