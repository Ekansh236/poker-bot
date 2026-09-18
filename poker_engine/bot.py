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


def decide_action(
    equity: float, amount_to_call: int, pot: int
) -> tuple[str, int]:
    """Turn an equity estimate + the current betting situation into an action.

    Returns (action, amount), where action is "fold", "call", "check", or
    "raise", matching the strings Round.apply_action() already expects.
    """
    # TODO(human): implement the decision logic.
    #
    # 1. If amount_to_call == 0, there's nothing to call -- breakeven_equity's
    #    division doesn't even make sense here (dividing by a call amount of
    #    zero). Decide what the bot does when checking is free: always check?
    #    Or bet/raise anyway if equity is strong, since nobody's forcing a
    #    decision either way?
    #
    # 2. Otherwise, call breakeven_equity(amount_to_call, pot) to get the
    #    threshold. Compare it against `equity`:
    #    - equity below the threshold -> folding is correct long-run.
    #    - equity at or above the threshold -> at least a call is justified.
    #
    # 3. Decide the margin above breakeven that justifies raising instead of
    #    just calling, and how much to raise. Keep it simple to start (e.g.
    #    a fixed pot fraction) -- you can make this more sophisticated later.
    pass
