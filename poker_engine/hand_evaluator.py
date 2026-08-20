from enum import IntEnum
from collections import Counter
from poker_engine.cards import Card, Suit, Rank

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
    
    if sorted_counts == [4, 1]:
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


