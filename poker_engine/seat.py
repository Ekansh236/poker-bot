from poker_engine.cards import Card, Rank, Suit
from poker_engine.display import card_to_ascii, hand_to_ascii

class Seat:
    def __init__(self, player, cards):
        self.player = player
        self.cards = cards

    def get_cards(self):
        return card_to_ascii(self.cards[0]) + " " + card_to_ascii(self.cards[1])
