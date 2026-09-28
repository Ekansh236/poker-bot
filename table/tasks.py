from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer

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
