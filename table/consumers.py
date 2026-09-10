import json

from channels.generic.websocket import AsyncWebsocketConsumer

from table import registry
from table.serializers import serialize_round


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

        # TODO(human): wire this up to locked_round() instead of a cached
        # self.round/self.seat (there is no such cache anymore -- connect()
        # no longer stores one, for exactly the reason we just discussed:
        # every locked_round() call deserializes brand-new Round/Seat objects,
        # so a Seat cached from connect() would never match by identity
        # inside a later, separately-loaded Round).
        #
        # Steps:
        #   1. Open `with registry.locked_round(self.table_id) as round_:`.
        #   2. Inside it, re-locate THIS connection's seat by calling
        #      registry.claim_seat(round_, self.player_id) again -- it's
        #      idempotent, an already-seated player just gets their existing
        #      seat back, freshly scoped to this round_.
        #   3. try/except ValueError around round_.apply_action(seat, action,
        #      amount), same shape as before:
        #        - on ValueError: self.send() the error to only this connection
        #        - on success: you'll want serialize_round(round_) for the
        #          broadcast -- build that payload while still inside the
        #          `with` block (round_ isn't valid to use once it exits),
        #          but the actual group_send() call can happen either inside
        #          or after the block ends -- your call.
        pass

    async def table_message(self, event):
        await self.send(text_data=json.dumps(event['message']))
