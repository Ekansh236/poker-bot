from poker_engine.cards import Card, Deck, Rank, Suit
from poker_engine.hand_evaluator import best_hand_from_seven
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
        self.pot = 0
        self.current_bet_to_match = 0
        self.current_turn_index = 0

    def deal_hole_cards(self):
        if RoundState.PRE_FLOP != self.current_round_state:
            raise ValueError("Hole cards can only be dealt during the PRE_FLOP round state.")
        for seat in self.seats:
            seat.cards = (self.deck.deal_card(), self.deck.deal_card())
            seat.has_acted_this_street = False  # Reset action status for the new hand
        self.current_bet_to_match = 0  # Reset the current bet to match for the new hand
        self.current_round_state = RoundState.FLOP  # Transition to FLOP state after dealing hole cards

    def burn_card(self):
        self.deck.deal_card()  # Burn a card (remove the top card from the deck)

    def flop_community_cards(self):
        if RoundState.FLOP == self.current_round_state:
            self.burn_card()  # Burn a card before the flop
            self.current_round_state = RoundState.TURN  # Transition to FLOP state
            self.community_cards.extend([self.deck.deal_card() for _ in range(3)])  # Deal 3 community cards
            self.current_bet_to_match = 0  # Reset the current bet to match for the new street
            for seat in self.seats:
                seat.has_acted_this_street = False  # Reset action status for all seats
                seat.bet_this_street = 0  # Reset the bet for all seats
            return self.community_cards
        raise ValueError("Flop can only be dealt during the FLOP round state.")

    def turn_community_card(self):
        if RoundState.TURN == self.current_round_state:
            self.burn_card()  # Burn a card before the turn
            self.current_round_state = RoundState.RIVER  # Transition to RIVER state
            self.community_cards.append(self.deck.deal_card())
            self.current_bet_to_match = 0  # Reset the current bet to match for the new street
            for seat in self.seats:
                seat.has_acted_this_street = False  # Reset action status for all seats
                seat.bet_this_street = 0  # Reset the bet for all seats
            return self.community_cards[-1]
        raise ValueError("Turn can only be dealt during the TURN round state.")

    def river_community_card(self):
        if RoundState.RIVER == self.current_round_state:
            self.burn_card()  # Burn a card before the river
            self.current_round_state = RoundState.SHOWDOWN  # Transition to SHOWDOWN state
            self.community_cards.append(self.deck.deal_card())
            self.current_bet_to_match = 0  # Reset the current bet to match for the new street
            for seat in self.seats:
                seat.has_acted_this_street = False  # Reset action status for all seats
                seat.bet_this_street = 0  # Reset the bet for all seats
            return self.community_cards[-1]
        raise ValueError("River can only be dealt during the RIVER round state.")

    def check_if_all_but_one_folded(self):
        active_seats = [seat for seat in self.seats if not seat.is_folded]
        return len(active_seats) == 1

    def refund_uncalled_bets(self):
        max_seat = max(self.seats, key=lambda seat: seat.total_contributed_to_pot)
        max_bet = max_seat.total_contributed_to_pot
        second_max_bet = max((seat.total_contributed_to_pot for seat in self.seats if seat != max_seat), default=0)
        if max_bet > second_max_bet and max_seat.is_folded != True:
            refund_amount = max_bet - second_max_bet
            max_seat.stack += refund_amount
            max_seat.total_contributed_to_pot = second_max_bet
            self.pot -= refund_amount

    def advance_turn(self):
        # Only finds the next seat that can still act -- it does NOT decide
        # or apply any betting action. That's apply_action()'s job.
        for _ in range(len(self.seats)):
            self.current_turn_index = (self.current_turn_index + 1) % len(self.seats)
            seat = self.seats[self.current_turn_index]
            if not seat.is_folded and not seat.is_all_in:
                return seat
        return None  # everyone else is folded or all-in -- no one left to act

    def apply_action(self, seat: Seat, action: str, amount: int = 0):
        if seat != self.seats[self.current_turn_index]:
            raise ValueError("It's not this seat's turn to act.")
        if action == "fold":
            seat.has_acted_this_street = True
            seat.fold()
            self.advance_turn()  # Move to the next seat after folding
        elif action == "call":
            seat.has_acted_this_street = True
            amount_to_call = self.current_bet_to_match - seat.bet_this_street
            actual_amount = seat.put_in_pot(amount_to_call)
            self.pot += actual_amount
            if self.advance_turn() == None:  # Move to the next seat after calling
                self.refund_uncalled_bets()
        elif action == "raise":
            seat.has_acted_this_street = True
            if amount + seat.bet_this_street <= self.current_bet_to_match:
                raise ValueError("Raise amount must be greater than the current bet to match.")
            actual_amount = seat.put_in_pot(amount)
            self.pot += actual_amount
            self.current_bet_to_match = seat.bet_this_street
            for other_seat in self.seats:
                if other_seat != seat:
                    other_seat.has_acted_this_street = False  # Reset action status for all other seats
            if self.advance_turn() == None:  # Move to the next seat after calling
                            self.refund_uncalled_bets()
        elif action == "check":
            seat.has_acted_this_street = True
            if seat.bet_this_street < self.current_bet_to_match:
                raise ValueError("Cannot check when there is a bet to match.")
            else:
                if self.advance_turn() == None:  # Move to the next seat after calling
                    self.refund_uncalled_bets()
        else:
            raise ValueError("Invalid action. Must be 'fold', 'call', or 'raise'.")

    def is_betting_round_complete(self):
        # A betting round is complete if all active seats have acted and either:
        # 1. All active seats have matched the current bet to match, or
        # 2. Only one active seat remains (everyone else has folded).
        active_seats = [seat for seat in self.seats if not seat.is_folded]
        if len(active_seats) <= 1:
            return True
        return all(seat.has_acted_this_street and seat.bet_this_street == self.current_bet_to_match for seat in active_seats)

    def compute_pots(self):
        levels = sorted(set(seat.total_contributed_to_pot for seat in self.seats if seat.total_contributed_to_pot > 0))
        pots = []
        previous_level = 0
        for level in levels:
            # Seats that contributed at least this deep paid into this layer.
            contributors = [seat for seat in self.seats if seat.total_contributed_to_pot >= level]
            pot_amount = (level - previous_level) * len(contributors)
            # Folded seats' chips still count toward pot_amount above, but they
            # can't be in the running to win the pot.
            eligible_seats = [seat for seat in contributors if not seat.is_folded]
            contributors.sort(key=lambda seat: self.seats.index(seat))  # Sort by original seat order
            pots.append((pot_amount, eligible_seats, contributors))
            previous_level = level
        return pots

    def showdown_resolution(self):
        pots = self.compute_pots()
        if self.check_if_all_but_one_folded():
            # If all but one player has folded, the remaining player wins the entire pot.
            winner = next(seat for seat in self.seats if not seat.is_folded)
            winner.stack += self.pot
            return [(winner, self.pot)]

        results = []
        for pot_amount, eligible_seats, contributors in pots:
            if not eligible_seats:
                for seat in contributors:
                    amount = pot_amount // len(contributors)
                    seat.stack += amount
                    results.append((seat, amount))
                continue
            best_hands = []
            for seat in eligible_seats:
                combined_cards = list(seat.cards) + self.community_cards
                _, hand_rank = best_hand_from_seven(combined_cards)
                best_hands.append((seat, hand_rank))

            # C: everyone tied for the best hand_rank on this specific pot wins it.
            best_rank = max(hand_rank for _, hand_rank in best_hands)
            winners = [seat for seat, hand_rank in best_hands if hand_rank == best_rank]

            # D: split the pot evenly; an indivisible remainder chip goes to the
            # first winner in seat order -- a simplification until dealer-button
            # position tracking exists to award it correctly.
            share = pot_amount // len(winners)
            remainder = pot_amount % len(winners)
            for i, seat in enumerate(winners):
                amount = share + (remainder if i == 0 else 0)
                seat.stack += amount
                results.append((seat, amount))

        return results