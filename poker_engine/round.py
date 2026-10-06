from poker_engine.cards import Card, Deck, Rank, Suit
from poker_engine.hand_evaluator import best_hand_from_seven
from poker_engine.seat import Seat
from enum import Enum
import time

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
        self.time_started = 0
        # Set only by advance_if_possible() when a showdown/fold-win JUST
        # resolved the hand it was called for; cleared at the start of every
        # apply_action_and_advance() call. An all-in runout deals every
        # remaining street AND starts the next hand within one call, so
        # without this, the board/winner from that resolved hand would never
        # be visible anywhere -- by the time the caller broadcasts, Round has
        # already moved on to a brand new hand.
        self.last_showdown = None
        # Stable identifier for the current hand -- incremented in
        # start_new_hand() and restart() too, and captured into
        # last_showdown by _resolve_showdown_and_start_new_hand() before
        # either of those overwrites it. table/persistence.py keys Hand
        # rows on (table, hand_number) using this value, so a retried
        # caller can't create duplicate persisted hands.
        self.current_hand_id = 1
        # Set once a hand resolves with some seat's stack at 0 -- no
        # bankroll/elimination handling exists beyond this, so heads-up the
        # game simply ends rather than trying to deal a broke player into
        # another hand (which they could never post a real blind for).
        self.game_over = False
        # Whoever most recently acted -- see apply_action() for the shape.
        # None until the first action of the game.
        self.last_action = None

    def _non_button_index(self):
        """The seat across from the button -- big blind, in heads-up."""
        return (self.button_index + 1) % len(self.seats)

    def deal_hole_cards(self):
        if RoundState.PRE_FLOP != self.current_round_state:
            raise ValueError("Hole cards can only be dealt during the PRE_FLOP round state.")

        # Heads-up and 3+-handed follow genuinely different blind/turn-order
        # rules, not just "more seats": heads-up, the button posts the small
        # blind and acts first preflop; 3+ handed, the button posts nothing,
        # the two seats after it post the blinds, and action starts with the
        # seat after the big blind (wrapping back to the button acting last
        # -- or, at exactly 3 seats, acting first again, since button+3
        # wraps to button+0). Postflop order needs no such split --
        # _non_button_index() as the first seat to act after the button is
        # already the general rule at any table size.
        if len(self.seats) == 2:
            small_blind_posted = self.seats[self.button_index].put_in_pot(self.SMALL_BLIND)
            big_blind_posted = self.seats[self._non_button_index()].put_in_pot(self.BIG_BLIND)
            self.pot += small_blind_posted + big_blind_posted
            self.current_turn_index = self.button_index  # Button acts first preflop
        else:
            small_blind_posted = self.seats[self._non_button_index()].put_in_pot(self.SMALL_BLIND)
            big_blind_posted = self.seats[(self.button_index + 2) % len(self.seats)].put_in_pot(self.BIG_BLIND)
            self.pot += small_blind_posted + big_blind_posted
            self.current_turn_index = (self.button_index + 3) % len(self.seats)

        self.current_bet_to_match = self.BIG_BLIND  # Always BIG_BLIND regardless of seat count.
        for seat in self.seats:
            seat.cards = (self.deck.deal_card(), self.deck.deal_card())
            seat.has_acted_this_street = False  # Reset action status for the new hand
        self.current_round_state = RoundState.FLOP  # Transition to FLOP state after dealing hole cards

    def start_new_hand(self):
        """Reset this Round in place and deal a fresh hand.

        Reuses the SAME Seat objects (preserving stacks -- winnings and
        losses carry forward) rather than building brand-new ones, which is
        exactly the gap Seat.reset_for_new_hand() was written for back in
        Milestone 2 but never actually got called anywhere until now.
        """
        self.current_hand_id += 1
        for seat in self.seats:
            seat.reset_for_new_hand()
        self.community_cards = []
        self.pot = 0
        self.deck = Deck()
        self.deck.shuffle()
        self.current_round_state = RoundState.PRE_FLOP
        self.button_index = self._non_button_index()  # Rotate the button
        self.deal_hole_cards()

    def restart(self, starting_stack: int = 500):
        """Reset every seat's stack and deal a brand new game from scratch.

        Unlike start_new_hand() (which preserves stacks across hands within
        one game), this exists for the play UI's Restart button -- wipe
        everything, including a game_over from a prior bust-out, and start
        over exactly like a freshly created table.
        """
        self.current_hand_id += 1
        for seat in self.seats:
            seat.stack = starting_stack
            seat.reset_for_new_hand()
        self.community_cards = []
        self.pot = 0
        self.deck = Deck()
        self.deck.shuffle()
        self.current_round_state = RoundState.PRE_FLOP
        self.button_index = 0
        self.game_over = False
        self.last_showdown = None
        self.last_action = None
        self.time_started = 0
        self.deal_hole_cards()

    def apply_action_and_advance(self, seat: Seat, action: str, amount: int = 0):
        """apply_action() followed by advance_if_possible(), as one call.

        Every caller that mutates live game state (WebSocket consumers,
        Celery tasks) needs both steps every time, in this order -- forgetting
        advance_if_possible() leaves current_turn_index pointing at a seat
        that already finished its street, which lets that seat act again on
        stale state (see the bot_decide_task bug this was written to fix).
        Kept as a separate method from apply_action() itself so the granular,
        single-action tests can still call apply_action() directly without
        triggering cascading street/hand transitions mid-assertion.
        """
        self.last_showdown = None
        self.apply_action(seat, action, amount)
        self.advance_if_possible()
        self.time_started = time.time()

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
        while self.is_betting_round_complete() and not self.game_over:
            if self.check_if_all_but_one_folded():
                self._resolve_showdown_and_start_new_hand()
            elif self.current_round_state == RoundState.FLOP:
                self.flop_community_cards()
            elif self.current_round_state == RoundState.TURN:
                self.turn_community_card()
            elif self.current_round_state == RoundState.RIVER:
                self.river_community_card()
            elif self.current_round_state == RoundState.SHOWDOWN:
                self._resolve_showdown_and_start_new_hand()

    def _resolve_showdown_and_start_new_hand(self):
        board = [card.to_dict() for card in self.community_cards]
        # A fold-win never reaches a real showdown -- the folded seat's
        # cards were never shown and shouldn't be revealed here, same as a
        # real poker table mucking a folded hand. Only include hole cards
        # when seats genuinely went to showdown against each other.
        is_real_showdown = not self.check_if_all_but_one_folded()
        hands = (
            {seat.player: [card.to_dict() for card in seat.cards] for seat in self.seats if not seat.is_folded}
            if is_real_showdown
            else {}
        )
        results = self.showdown_resolution()
        self.last_showdown = {
            "board": board,
            "results": [{"player": seat.player, "amount": amount} for seat, amount in results],
            "hands": hands,
            # Captured HERE, before start_new_hand() runs below and
            # overwrites current_hand_id with the NEXT hand's id -- the
            # same ordering trap last_showdown itself exists to avoid for
            # the client.
            "hand_id": self.current_hand_id,
        }
        # TODO(human): "any seat busted -> whole game over" was fine at a
        # 2-seat table (busting IS losing), but at 3+ seats it currently
        # ends the game for everyone the moment the FIRST player busts, even
        # with several others still holding chips. The real end condition
        # is "fewer than 2 seats still have a stack > 0".
        #
        # A busted seat needs to be excluded from every future hand, not
        # just skipped once: no cards dealt to it, no blind posted by or to
        # it, never the button, never on the clock. The tricky part is that
        # reset_for_new_hand() unconditionally clears is_folded and
        # is_all_in at the start of every hand -- so a busted seat (stack
        # 0, currently indistinguishable from "folded" or "all-in" once the
        # hand that busted it ends) would silently come back to life next
        # hand unless something marks it as OUT in a way that survives
        # reset_for_new_hand(), not just this hand's state.
        #
        # That's the actual design decision: do you check `seat.stack <= 0`
        # directly everywhere a seat's eligibility already gets checked
        # (deal_hole_cards()'s blind posting, start_new_hand()'s button
        # rotation via _non_button_index(), advance_turn()'s folded/all-in
        # skip), or introduce a dedicated flag (e.g. is_eliminated) set once
        # and never cleared by reset_for_new_hand()? Either can work --
        # pick one and apply it consistently at all three of those call
        # sites, not just the end-condition check below.
        #
        # Must still: end the game (self.game_over = True, self.pot = 0,
        # same as today) once only one seat has chips left, and otherwise
        # call self.start_new_hand() as today.

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
        if self.game_over:
            raise ValueError("The game is over -- one seat is out of chips.")
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
            # put_in_pot() silently caps at the seat's stack -- the validation
            # above checked the REQUESTED amount, not what actually got put
            # in. A short all-in "raise" that lands below current_bet_to_match
            # (e.g. its stack couldn't cover the requested amount) must never
            # lower the bar for whoever already bet more, and doesn't
            # genuinely reopen the betting round -- there's nothing new for
            # them to respond to.
            if seat.bet_this_street > self.current_bet_to_match:
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

        # Whoever just acted -- persists across broadcasts (not a one-shot
        # event like last_showdown) so a client can show an ongoing "what
        # did the other seat just do" log, not just flash it once.
        self.last_action = {
            "player": seat.player,
            "action": action,
            "bet_this_street": seat.bet_this_street,
            "is_all_in": seat.is_all_in,
        }

    def is_betting_round_complete(self):
        # A betting round is complete if all active seats have acted and either:
        # 1. All active seats have matched the current bet to match, or
        # 2. Only one active seat remains (everyone else has folded).
        active_seats = [seat for seat in self.seats if not seat.is_folded]
        if len(active_seats) <= 1:
            return True

        # A short all-in (fewer chips than current_bet_to_match) can never
        # satisfy an exact bet-match -- it's the seat's whole stack, that's
        # already the most they can ever contribute. Once at most one seat
        # can still voluntarily act (everyone else folded or all-in), no one
        # is left to bet against, so has_acted_this_street stops mattering
        # too: it gets reset to False by every later street's dealing (e.g.
        # flop_community_cards()) even though there's no new decision left
        # to make, which would otherwise stall the runout after just one
        # street. Matching current_bet_to_match is still required, since
        # that's what distinguishes "already caught up" from "still owes a
        # call against a fresh raise they haven't responded to yet".
        seats_that_can_still_act = [seat for seat in active_seats if not seat.is_all_in]
        if len(seats_that_can_still_act) <= 1:
            return all(seat.bet_this_street == self.current_bet_to_match for seat in seats_that_can_still_act)

        return all(seat.has_acted_this_street and seat.bet_this_street == self.current_bet_to_match for seat in seats_that_can_still_act)

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