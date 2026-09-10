from poker_engine.cards import Card, Rank, Suit
from poker_engine.display import card_to_ascii, hand_to_ascii

class Seat:
    def __init__(self, player, cards):
        self.player = player
        self.cards = cards
        self.stack = 500
        self.bet_this_street = 0
        self.is_folded = False
        self.is_all_in = False
        self.has_acted_this_street = False
        self.total_contributed_to_pot = 0

    def get_cards(self):
        return card_to_ascii(self.cards[0]) + " " + card_to_ascii(self.cards[1])

    def fold(self):
        self.is_folded = True

    def put_in_pot(self, amount):
        # Caller (Round) is responsible for validating legality against the
        # round's current bet-to-match -- this only applies the consequences.
        actual_amount = min(amount, self.stack)
        self.stack -= actual_amount
        self.bet_this_street += actual_amount
        self.total_contributed_to_pot += actual_amount
        if self.stack == 0:
            self.is_all_in = True
        return actual_amount

    def reset_for_new_hand(self):
        self.bet_this_street = 0
        self.is_folded = False
        self.is_all_in = False
        self.total_contributed_to_pot = 0
        