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
    SMALL_BLIND = 5
    BIG_BLIND = 10

    def __init__(self, seats: list[Seat], deck: Deck):
        self.seats = seats
        self.deck = deck
        self.community_cards = []
        self.current_round_state = RoundState.PRE_FLOP
        self.pot = 0
        self.current_bet_to_match = 0
        self.current_turn_index = 0
        self.button_index = 0

    def _non_button_index(self):
        """The seat across from the button -- big blind, in heads-up."""
        return (self.button_index + 1) % len(self.seats)

    def deal_hole_cards(self):
        if RoundState.PRE_FLOP != self.current_round_state:
            raise ValueError("Hole cards can only be dealt during the PRE_FLOP round state.")

        # Button posts the small blind, the other seat posts the big blind.
        small_blind_posted = self.seats[self.button_index].put_in_pot(self.SMALL_BLIND)
        big_blind_posted = self.seats[self._non_button_index()].put_in_pot(self.BIG_BLIND)
        self.pot += small_blind_posted + big_blind_posted

        for seat in self.seats:
            seat.cards = (self.deck.deal_card(), self.deck.deal_card())
            seat.has_acted_this_street = False  # Reset action status for the new hand
        self.current_bet_to_match = self.BIG_BLIND  # Reset the current bet to match for the new hand
        self.current_round_state = RoundState.FLOP  # Transition to FLOP state after dealing hole cards
        self.current_turn_index = self.button_index  # Button acts first preflop

    def start_new_hand(self):
        """Reset this Round in place and deal a fresh hand.

        Reuses the SAME Seat objects (preserving stacks -- winnings and
        losses carry forward) rather than building brand-new ones, which is
        exactly the gap Seat.reset_for_new_hand() was written for back in
        Milestone 2 but never actually got called anywhere until now.
        """
        for seat in self.seats:
            seat.reset_for_new_hand()
        self.community_cards = []
        self.pot = 0
        self.deck = Deck()
        self.deck.shuffle()
        self.current_round_state = RoundState.PRE_FLOP
        self.button_index = self._non_button_index()  # Rotate the button
        self.deal_hole_cards()

    def advance_if_possible(self):
        """Auto-advance as far as the current state allows.

        Call this after every apply_action(). Loops -- dealing the next
        street, resolving a fold-win or showdown, or starting a brand new
        hand -- until it reaches a point where a real player actually has
        to act again, or nothing more can happen automatically.

        This is the piece that turns "the engine CAN progress a hand" into
        "the hand actually progresses" -- deal_hole_cards(),
        flop_community_cards(), showdown_resolution(), start_new_hand(),
        etc. all already exist and work; nothing has ever chained them
        together automatically until now.
        """
        # TODO(human): implement this.
        #
        # The loop condition is self.is_betting_round_complete() -- keep
        # advancing as long as it's True. Each iteration needs to pick the
        # right next step:
        #
        # 1. Fold-win check FIRST, every iteration: if
        #    self.check_if_all_but_one_folded(), the hand is over right
        #    now regardless of what street we're on -- call
        #    self.showdown_resolution() (it doesn't require any particular
        #    current_round_state to run), then self.start_new_hand().
        #
        # 2. Otherwise, branch on self.current_round_state to call the
        #    right next method -- remember the state naming is offset by
        #    one from what you'd expect (current_round_state == FLOP means
        #    "preflop betting just finished, deal the flop next", not
        #    "we're currently on the flop"). Check what each of
        #    flop_community_cards()/turn_community_card()/
        #    river_community_card()'s own `if` guards require.
        #
        # 3. When current_round_state == SHOWDOWN, that's the river betting
        #    having just completed -- call self.showdown_resolution() then
        #    self.start_new_hand(), same as the fold-win case.
        #
        # Trust the loop to terminate correctly on its own: think about
        # why is_betting_round_complete() naturally becomes False right
        # after any of these steps runs (what do flop_community_cards()
        # and start_new_hand()/deal_hole_cards() both already do to every
        # seat's has_acted_this_street?) -- that's what stops the loop
        # once a real player needs to act.
        pass

    def burn_card(self):
        self.deck.deal_card()  # Burn a card (remove the top card from the deck)

    def flop_community_cards(self):
        if RoundState.FLOP == self.current_round_state:
            self.burn_card()  # Burn a card before the flop
            self.current_round_state = RoundState.TURN  # Transition to FLOP state
            self.community_cards.extend([self.deck.deal_card() for _ in range(3)])  # Deal 3 community cards
            self.current_bet_to_match = 0  # Reset the current bet to match for the new street
            self.current_turn_index = self._non_button_index()  # Big blind acts first postflop
            for seat in self.seats:
                seat.has_acted_this_street = False  # Reset action status for all seats
                seat.bet_this_street = 0  # Reset the bet for all seats
            return self.community_cards
        raise ValueError("Flop can only be dealt during the FLOP round state.")

    def turn_community_card(self):
        if RoundState.TURN == self.current_round_state:
            self.current_turn_index = self._non_button_index()  # Big blind acts first postflop
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
            self.current_turn_index = self._non_button_index()  # Big blind acts first postflop
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