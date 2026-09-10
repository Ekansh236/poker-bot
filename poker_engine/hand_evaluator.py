from enum import IntEnum
from collections import Counter
from poker_engine.cards import Card, Suit, Rank
from itertools import combinations

class Hands(IntEnum):
    HIGH_CARD = 1
    ONE_PAIR = 2
    TWO_PAIR = 3
    THREE_OF_A_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_A_KIND = 8
    STRAIGHT_FLUSH = 9
    ROYAL_FLUSH = 10

def evaluate_hand(cards):
    # Placeholder for hand evaluation logic
    # This function should analyze the given cards and return the best hand type
    # For now, it returns HIGH_CARD as a default
    sorted_cards = sorted(cards, key=lambda card: card.rank, reverse=True)
    card_rank_counts = Counter(card.rank for card in sorted_cards)

    #Check shape of the hand
    counts = list(card_rank_counts.values())
    sorted_counts = sorted(counts, reverse=True)

    # Ace-low "wheel" straight (A-2-3-4-5) is the one case where Ace plays
    # LOW instead of high, so the normal max-rank - min-rank == 4 check
    # can't detect it -- Ace's numeric value (14) breaks the math.
    hand_ranks = {card.rank for card in sorted_cards}
    is_wheel = hand_ranks == {Rank.ACE, Rank.FIVE, Rank.FOUR, Rank.THREE, Rank.TWO}
    is_normal_straight = len(sorted_counts) == 5 and sorted_cards[0].rank - sorted_cards[4].rank == 4
    is_straight = is_normal_straight or is_wheel

    # For the wheel, the Ace ranks LOWEST, so it goes last (not first) in the
    # tiebreaker list -- otherwise it would incorrectly outrank a 6-high straight.
    straight_ranks = [Rank.FIVE, Rank.FOUR, Rank.THREE, Rank.TWO, Rank.ACE] if is_wheel \
        else [card.rank for card in sorted_cards]

    if cards[0].suit == cards[1].suit == cards[2].suit == cards[3].suit == cards[4].suit:
        if is_normal_straight and sorted_cards[0].rank == Rank.ACE and sorted_cards[1].rank == Rank.KING and sorted_cards[2].rank == Rank.QUEEN and sorted_cards[3].rank == Rank.JACK and sorted_cards[4].rank == Rank.TEN:
            return (Hands.ROYAL_FLUSH, [card.rank for card in sorted_cards])
        elif is_straight:
            return (Hands.STRAIGHT_FLUSH, straight_ranks)
        else:
            return (Hands.FLUSH, [card.rank for card in sorted_cards])
    elif is_straight:
        return (Hands.STRAIGHT, straight_ranks)
    elif sorted_counts == [4, 1]:
        return (Hands.FOUR_OF_A_KIND, [rank for rank, count in card_rank_counts.items() if count == 4][0], [rank for rank, count in card_rank_counts.items() if count == 1])
    elif sorted_counts == [3, 2]:
        return (Hands.FULL_HOUSE, [rank for rank, count in card_rank_counts.items() if count == 3][0], [rank for rank, count in card_rank_counts.items() if count == 2])
    elif sorted_counts == [3, 1, 1]:
        return (Hands.THREE_OF_A_KIND, [rank for rank, count in card_rank_counts.items() if count == 3][0], [rank for rank, count in card_rank_counts.items() if count == 1])
    elif sorted_counts == [2, 2, 1]:
        return (Hands.TWO_PAIR, [rank for rank, count in card_rank_counts.items() if count == 2], [rank for rank, count in card_rank_counts.items() if count == 1])
    elif sorted_counts == [2, 1, 1, 1]:
        return (Hands.ONE_PAIR, [rank for rank, count in card_rank_counts.items() if count == 2], [rank for rank, count in card_rank_counts.items() if count == 1])
    elif sorted_counts == [1, 1, 1, 1, 1]:
        return (Hands.HIGH_CARD, [rank for rank, count in card_rank_counts.items() if count == 1])


def best_hand_from_seven(cards):
    combos = combinations(cards, 5)
    best_hand = None
    best_hand_rank = None
    for combo in combos:
        hand_rank = evaluate_hand(combo)
        if best_hand is None or hand_rank > best_hand_rank:
            best_hand = combo
            best_hand_rank = hand_rank
    return best_hand, best_hand_rank



