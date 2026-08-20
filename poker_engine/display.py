# Console/testing helpers only — not part of the domain model.
# Kept separate from cards.py so the engine has zero presentation concerns.

from poker_engine.cards import Card, Rank, Suit

_RANK_DISPLAY = {
    Rank.TWO: "2", Rank.THREE: "3", Rank.FOUR: "4", Rank.FIVE: "5",
    Rank.SIX: "6", Rank.SEVEN: "7", Rank.EIGHT: "8", Rank.NINE: "9",
    Rank.TEN: "10", Rank.JACK: "J", Rank.QUEEN: "Q", Rank.KING: "K", Rank.ACE: "A",
}

_SUIT_SYMBOL = {
    Suit.HEARTS: "♥", Suit.DIAMONDS: "♦", Suit.CLUBS: "♣", Suit.SPADES: "♠",
}


def card_to_ascii(card: Card) -> str:
    rank = _RANK_DISPLAY[card.rank]
    suit = _SUIT_SYMBOL[card.suit]
    top = f"{rank:<2}"
    bottom = f"{rank:>2}"
    return (
        "┌─────┐\n"
        f"│{top}   │\n"
        f"│  {suit}  │\n"
        f"│   {bottom}│\n"
        "└─────┘"
    )


def hand_to_ascii(cards: list[Card]) -> str:
    blocks = [card_to_ascii(c).split("\n") for c in cards]
    return "\n".join(" ".join(block[row] for block in blocks) for row in range(5))

