# Milestone 4 -- autonomous bot decision-making. Pure Python, no framework
# dependencies, same as poker_engine's other modules.

import random

from poker_engine.cards import Card, Rank, Suit
from poker_engine.hand_evaluator import best_hand_from_seven


def _unseen_cards(known_cards: list[Card]) -> list[Card]:
    """Every card not already visible to the bot.

    Built from a fresh full deck, NOT from a live Round's Deck object --
    that deck has already had every seat's real hole cards physically dealt
    out of it, which would let the simulation quietly "know" which specific
    cards opponents are NOT holding. The bot must treat every card it
    can't see as equally possible, same as a human player would.
    """
    full_deck = [Card(rank, suit) for suit in Suit for rank in Rank]
    return [card for card in full_deck if card not in known_cards]


def estimate_equity(
    hole_cards: tuple[Card, Card],
    community_cards: list[Card],
    num_opponents: int = 1,
    num_trials: int = 1000,
) -> float:
    """Monte Carlo estimate of this hand's win probability."""
    unseen_cards = _unseen_cards(list(hole_cards) + community_cards)
    num_board_cards_needed = 5 - len(community_cards)
    num_simulated_cards = num_board_cards_needed + num_opponents * 2
    num_wins = 0
    num_losses = 0
    for i in range(num_trials):
        sampled_cards = random.sample(unseen_cards, num_simulated_cards)
        original_community_cards = community_cards.copy()
        for k in range(num_board_cards_needed):
            original_community_cards.append(sampled_cards[k])

        sampled_hole_cards = sampled_cards[num_board_cards_needed:]
        _, bot_rank = best_hand_from_seven(list(hole_cards) + original_community_cards)
        opponent_ranks = []
        for k in range(0, num_opponents * 2, 2):
            opponent_hole_cards = sampled_hole_cards[k : k + 2]
            _, opponent_rank = best_hand_from_seven(
                list(opponent_hole_cards) + original_community_cards
            )
            opponent_ranks.append(opponent_rank)

        best_opponent_rank = max(opponent_ranks)
        if bot_rank > best_opponent_rank:
            num_wins += 1
        elif bot_rank == best_opponent_rank:
            num_wins += 0.5
        else:
            num_losses += 1

    return num_wins / num_trials


def breakeven_equity(amount_to_call: int, pot: int) -> float:
    """The minimum win probability needed for calling to be worth it.

    Standard pot-odds formula: you're risking `amount_to_call` to win a pot
    that will be `pot + amount_to_call` once you've called it. Below this
    equity, calling loses money on average in the long run; above it, calling
    is profitable even if you lose this particular hand more often than not.
    """
    return amount_to_call / (pot + amount_to_call)

def clamp(value, low, high):
    return max(low, min(value, high))

def p_value(equity, x_lo, x_hi, p_lo, p_hi):
    """Clamped linear interpolation from equity onto a raise probability.

    Flat at p_lo below x_lo, flat at p_hi above x_hi, interpolated between.
    Returns the probability itself -- sampling it with random.random() is
    the caller's job, same contract as breakeven_equity().
    """
    fraction = clamp((equity - x_lo) / (x_hi - x_lo), 0, 1)
    return p_lo + fraction * (p_hi - p_lo)

def p_bluff(bet_size, pot):
    """Damped, capped version of the optimal bluff-to-value ratio.

    bet_size / (pot + 2*bet_size) is the frequency that makes a caller
    indifferent between calling and folding -- an aggressive baseline.
    Damping it and capping it keeps this bot's bluffing occasional rather
    than textbook-optimal.
    """
    raw = bet_size / (pot + 2 * bet_size)
    return min(0.4 * raw, 0.18)

def decide_action(
    equity: float, amount_to_call: int, pot: int, is_button: bool = False
) -> tuple[str, int]:
    """Turn an equity estimate + the current betting situation into an action.

    Returns (action, amount), where action is "fold", "call", "check", or
    "raise", matching the strings Round.apply_action() already expects.
    """
    # Position adjustment: the button will have the information advantage
    # of acting last for the rest of the hand, so it's worth playing
    # slightly looser (lower thresholds); out of position, slightly
    # tighter (higher thresholds). 0.02 is a starting value, not a derived
    # one -- there's no exact formula for this, unlike breakeven_equity().
    position_adjustment = -0.02 if is_button else 0.02
    value_threshold = 0.60

    if amount_to_call == 0:
        x_lo = value_threshold + position_adjustment
        x_hi = 0.9
        p_lo = 0.03
        p_hi = 0.6
        raise_probability = p_value(equity, x_lo, x_hi, p_lo, p_hi)
        bet_size = pot // 2 if pot > 0 else 10
        bluff_probability = p_bluff(bet_size, pot)
        if random.random() < raise_probability:
            return ("raise", bet_size)
        elif random.random() < bluff_probability:
            return ("raise", bet_size)
        else:
            return ("check", 0)
    else:
        fold_cutoff = breakeven_equity(amount_to_call, pot) + position_adjustment
        x_lo = fold_cutoff + 0.15
        x_hi = x_lo + 0.25
        p_lo = 0.03
        p_hi = 0.55
        raise_probability = p_value(equity, x_lo, x_hi, p_lo, p_hi)
        bet_size = amount_to_call + (pot // 2 if pot > 0 else 10)
        bluff_probability = p_bluff(bet_size, pot)
        if random.random() < raise_probability:
            return ("raise", bet_size)
        elif equity < fold_cutoff:
            if random.random() < bluff_probability:
                return ("raise", bet_size)
            else:
                return ("fold", 0)
        else:
            return ("call", amount_to_call)



def bot_decide(round_, seat) -> tuple[str, int]:
    """Given a live Round and this bot's Seat, decide what to do.

    Pulls the real values estimate_equity() and decide_action() need off
    the live game objects, then chains the two together.
    """
    hole_cards = seat.cards
    community_cards = round_.community_cards
    num_opponents = sum(
        1 for s in round_.seats if s != seat and not s.is_folded
    )
    if num_opponents == 0:
        # If there are no opponents, the bot can check or bet freely.
        return ("check", 0)
    amount_to_call = round_.current_bet_to_match - seat.bet_this_street
    pot = round_.pot
    is_button = round_.seats[round_.button_index] is seat
    equity = estimate_equity(hole_cards, community_cards, num_opponents, num_trials=1000)
    return decide_action(equity, amount_to_call, pot, is_button)

