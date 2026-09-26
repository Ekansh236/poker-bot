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
    # TODO(human): implement this task.
    #
    # 1. Open `with registry.locked_round(table_id) as round_:` -- same
    #    Redis-backed lock/read/write cycle every other access to shared
    #    game state already goes through. A Celery worker is just another
    #    separate process; it's subject to the exact same lost-update risk
    #    as any other process touching Round state directly.
    #
    # 2. Find this bot's seat inside that round_ -- registry.claim_seat is
    #    idempotent, same pattern consumers.py already uses.
    #
    # 3. Call bot_decide(round_, seat) to get (action, amount).
    #
    # 4. Apply it: round_.apply_action(seat, action, amount). Think about
    #    what should happen if this raises ValueError -- can a bot's own
    #    decide_action() ever produce an illegal action here, given what
    #    you already know about how decide_action() and Round.apply_action()
    #    are related?
    #
    # 5. Broadcast the result: get the channel layer with
    #    get_channel_layer(), then call group_send() on it -- but
    #    group_send() is async and this function is a plain sync Celery
    #    task, so wrap the call with async_to_sync(...)(...). Use the same
    #    group name convention and {'type': 'table_message', 'message': ...}
    #    shape consumers.py already established, with serialize_round(round_)
    #    as the payload.
    with registry.locked_round(table_id) as round_:
        bot_seat = registry.claim_seat(round_, player_id=player_id)
        action, amount = bot_decide(round_=round_, seat=bot_seat)
        round_.apply_action(seat=bot_seat, action=action, amount=amount)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'table_{table_id}',
            {"type": "table_message", "message": serialize_round(round_)}
        )
    

