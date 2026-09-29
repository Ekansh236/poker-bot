from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
import time

from poker_engine.bot import bot_decide
from table import registry
from table.serializers import serialize_round


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
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'table_{table_id}',
            {"type": "table_message", "message": serialize_round(round_)}
        )


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
                round_.apply_action_and_advance(seat=round_.seats[round_.current_turn_index], action="fold", amount=0)
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'table_{table_id}',
                    {"type": "table_message", "message": serialize_round(round_)}
                )
