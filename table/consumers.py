import json

from channels.generic.websocket import AsyncWebsocketConsumer

from table import registry
from table.serializers import serialize_round


class TableConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.table_id = self.scope['url_route']['kwargs']['table_id']
        self.player_id = self.scope['url_route']['kwargs']['player_id']
        self.group_name = f'table_{self.table_id}'

        self.round = registry.get_round(self.table_id)
        self.seat = registry.claim_seat(self.round, self.player_id)

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # TODO(human): parse the incoming action message and apply it.
        #
        # 1. json.loads(text_data) to get the client's message. Decide the
        #    shape yourself -- e.g. {"action": "raise", "amount": 50}.
        # 2. Call self.round.apply_action(self.seat, action, amount).
        # 3. On success: broadcast the new public state to the whole table
        #    via self.channel_layer.group_send(self.group_name, {...}) --
        #    use serialize_round(self.round) as the payload, and route it
        #    through the table_message handler below (type: 'table_message').
        # 4. On failure (Round.apply_action raises ValueError for illegal
        #    actions -- out-of-turn, can't check facing a bet, etc.): send
        #    the error back to ONLY this connection via self.send(), not
        #    group_send -- other players shouldn't see your invalid attempts.
        pass

    async def table_message(self, event):
        await self.send(text_data=json.dumps(event['message']))
