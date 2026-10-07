import time

import structlog
from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer

from poker_engine.bot import bot_decide
from table import registry
from table.persistence import persist_hand_result
from table.serializers import serialize_round

log = structlog.get_logger(__name__)

# How long a bot's turn stays visibly "on the clock" (current_turn pointing
# at it, seat glowing) before its action actually fires. Scheduled via
# apply_async(countdown=...) rather than time.sleep() -- this worker runs
# --pool=solo, so a real sleep would block every other table's bots too,
# not just this one's.
BOT_ACTION_DELAY_SECONDS = 4


@shared_task
def bot_decide_task(table_id: str, player_id: str) -> None:
    """Run a bot's decision and broadcast the result to the table.

    Runs on a Celery worker -- a completely separate process from any
    TableConsumer. Takes plain, JSON-serializable arguments (table_id,
    player_id), not live Round/Seat objects, since those can't cross a
    process boundary as task arguments.
    """
    with registry.locked_round(table_id) as round_:
        bot_seat = registry.claim_seat(round_, player_id=player_id)
        action, amount = bot_decide(round_=round_, seat=bot_seat)
        round_.apply_action_and_advance(seat=bot_seat, action=action, amount=amount)
        log.info("bot_action_applied", table_id=table_id, player_id=player_id, action=action, amount=amount)
        if round_.last_showdown:
            persist_hand_result(table_id, round_)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'table_{table_id}',
            {"type": "table_message", "message": serialize_round(round_)}
        )

        # A bot's own action can leave it still on the clock -- e.g. the big
        # blind checking to close preflop betting immediately becomes their
        # own turn again postflop, since the non-button acts first on every
        # street after preflop. Nothing else re-dispatches this task in that
        # case: consumers.receive() only fires on a real player's message.
        next_seat = round_.seats[round_.current_turn_index]
        if next_seat.is_bot:
            bot_decide_task.apply_async(args=[table_id, next_seat.player], countdown=BOT_ACTION_DELAY_SECONDS)


@shared_task
def check_turn_timeouts() -> None:
    """Fired by Celery Beat on a fixed interval (see config/celery.py).

    For every table with a live Round, check whether whoever's seat is on
    the clock (round_.seats[round_.current_turn_index]) has been sitting
    there too long, and if so, apply a default action on their behalf.
    """
    for table_id in registry.all_table_ids():
        with registry.locked_round(table_id) as round_:
            # A Round pickled before `time_started` existed won't have it --
            # pickle restores a saved __dict__ directly, it doesn't re-run
            # __init__(). Don't let one old/malformed table crash the whole
            # periodic tick for every other table.
            time_started = getattr(round_, "time_started", 0)
            if time.time() - time_started > 30:
                timed_out_player = round_.seats[round_.current_turn_index].player
                round_.apply_action_and_advance(seat=round_.seats[round_.current_turn_index], action="fold", amount=0)
                log.info("turn_timed_out", table_id=table_id, player_id=timed_out_player)
                if round_.last_showdown:
                    persist_hand_result(table_id, round_)
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'table_{table_id}',
                    {"type": "table_message", "message": serialize_round(round_)}
                )

                # Same gap as bot_decide_task: a fold-driven advance (new
                # street, or a whole new hand after a fold-win) can land
                # squarely on a bot's turn with nothing else to dispatch it.
                next_seat = round_.seats[round_.current_turn_index]
                if next_seat.is_bot:
                    bot_decide_task.apply_async(args=[table_id, next_seat.player], countdown=BOT_ACTION_DELAY_SECONDS)
