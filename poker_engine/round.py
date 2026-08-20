from poker_engine.cards import Card, Deck, Rank, Suit
from poker_engine.seat import Seat
from enum import Enum

class RoundState(Enum):
    PRE_FLOP = 1
    FLOP = 2
    TURN = 3
    RIVER = 4
    SHOWDOWN = 5

class Round:
    def __init__(self, seats: list[Seat], deck: Deck):
        self.seats = seats
        self.deck = deck
        self.community_cards = []
        self.current_round_state = RoundState.PRE_FLOP

    def deal_hole_cards(self):
        if RoundState.PRE_FLOP != self.current_round_state:
            raise ValueError("Hole cards can only be dealt during the PRE_FLOP round state.")
        for seat in self.seats:
            seat.cards = (self.deck.deal_card(), self.deck.deal_card())
        self.current_round_state = RoundState.FLOP  # Transition to FLOP state after dealing hole cards

    def burn_card(self):
        self.deck.deal_card()  # Burn a card (remove the top card from the deck)

    def flop_community_cards(self):
        if RoundState.FLOP == self.current_round_state:
            self.burn_card()  # Burn a card before the flop
            self.current_round_state = RoundState.TURN  # Transition to FLOP state
            self.community_cards.extend([self.deck.deal_card() for _ in range(3)])  # Deal 3 community cards
            return self.community_cards
        raise ValueError("Flop can only be dealt during the FLOP round state.")

    def turn_community_card(self):
        if RoundState.TURN == self.current_round_state:
            self.burn_card()  # Burn a card before the turn
            self.current_round_state = RoundState.RIVER  # Transition to RIVER state
            self.community_cards.append(self.deck.deal_card())
            return self.community_cards[-1]
        raise ValueError("Turn can only be dealt during the TURN round state.")

    def river_community_card(self):
        if RoundState.RIVER == self.current_round_state:
            self.burn_card()  # Burn a card before the river
            self.current_round_state = RoundState.SHOWDOWN  # Transition to SHOWDOWN state
            self.community_cards.append(self.deck.deal_card())
            return self.community_cards[-1]
        raise ValueError("River can only be dealt during the RIVER round state.")