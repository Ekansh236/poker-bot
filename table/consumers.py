import json

from channels.generic.websocket import AsyncWebsocketConsumer

from table import registry
from table.serializers import serialize_round
from table.tasks import bot_decide_task


class TableConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.table_id = self.scope['url_route']['kwargs']['table_id']
        self.player_id = self.scope['url_route']['kwargs']['player_id']
        self.group_name = f'table_{self.table_id}'

        # Claiming a seat mutates shared state (two players racing for the
        # last open seat is the same lost-update risk as betting actions),
        # so it must happen under the lock too -- see registry.locked_round.
        with registry.locked_round(self.table_id) as round_:
            registry.claim_seat(round_, self.player_id)
            registry.seat_bot_if_needed(round_)

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")
        amount = data.get("amount")

        with registry.locked_round(self.table_id) as round_:
            seat = registry.claim_seat(round_, self.player_id)
            try:
                round_.apply_action(seat, action, amount)
            except ValueError as e:
                await self.send(text_data=json.dumps({"error": str(e)}))
                return

            # Broadcast the updated round state to all players at the table.
            broadcast_payload = serialize_round(round_)
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "table.message",
                    "message": broadcast_payload,
                },
            )

            # TODO(human): if it's now a bot's turn, dispatch the task.
            #
            # Check round_.seats[round_.current_turn_index].is_bot. If it's
            # True, call bot_decide_task.delay(self.table_id, <that seat's
            # player_id>) -- .delay() is Celery's real async enqueue (unlike
            # sub-step 4's direct-call testing, this actually requires a
            # running `celery -A config worker` process to pick it up).
            #
            # Worth reasoning through before you write this: you're still
            # inside `with registry.locked_round(self.table_id) as round_:`
            # right now, meaning THIS process is still holding the Redis
            # lock. bot_decide_task will try to acquire that same lock
            # itself the moment a worker picks it up. Does dispatching here,
            # before this `with` block exits, cause a problem? Walk through
            # what actually happens to the task while this lock is held.
            if round_.seats[round_.current_turn_index].is_bot:
                bot_decide_task.delay(self.table_id, round_.seats[round_.current_turn_index].player)
                

    async def table_message(self, event):
        await self.send(text_data=json.dumps(event['message']))
