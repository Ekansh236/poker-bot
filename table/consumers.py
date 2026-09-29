import json

import structlog
from channels.generic.websocket import AsyncWebsocketConsumer

from table import registry
from table.serializers import serialize_hand, serialize_round
from table.tasks import bot_decide_task

log = structlog.get_logger(__name__)


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

            # A brand-new table has no hand in progress yet -- nothing
            # auto-deals the very first hand (see README's Known gaps).
            # Once every seat is filled and no one has cards, deal one now
            # so a freshly opened table is immediately playable.
            if all(seat.player is not None for seat in round_.seats) and all(
                seat.cards is None for seat in round_.seats
            ):
                round_.deal_hole_cards()

            state_payload = serialize_round(round_)

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        # Push current state straight to this connection -- nothing else
        # broadcasts until someone acts, and this client needs to see the
        # table (including a hand it may have just caused to be dealt)
        # immediately, not wait for the next action anywhere at the table.
        await self.send(text_data=json.dumps(state_payload))
        log.info("player_connected", table_id=self.table_id, player_id=self.player_id)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        log.info("player_disconnected", table_id=self.table_id, player_id=self.player_id, close_code=close_code)

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data.get("type") == "get_hand":
            # Hole cards are never part of the shared broadcast (see
            # serialize_round) -- a client asks for its own hand explicitly,
            # any time its view of the table might be stale (after any
            # action from anyone, including the bot or a timeout auto-fold,
            # since a new hand may have just been dealt).
            with registry.locked_round(self.table_id) as round_:
                seat = registry.claim_seat(round_, self.player_id)
                hand_payload = serialize_hand(seat)
            await self.send(text_data=json.dumps({"type": "hole_cards", "cards": hand_payload}))
            return

        if data.get("type") == "restart":
            # A dedicated path, not apply_action_and_advance() -- restart
            # needs to work even after game_over, which apply_action()
            # deliberately refuses to process as a normal turn-based action.
            with registry.locked_round(self.table_id) as round_:
                registry.claim_seat(round_, self.player_id)
                registry.seat_bot_if_needed(round_)
                round_.restart()
                log.info("table_restarted", table_id=self.table_id, player_id=self.player_id)
                broadcast_payload = serialize_round(round_)
                await self.channel_layer.group_send(
                    self.group_name,
                    {"type": "table.message", "message": broadcast_payload},
                )
                if round_.seats[round_.current_turn_index].is_bot:
                    bot_decide_task.delay(self.table_id, round_.seats[round_.current_turn_index].player)
            return

        action = data.get("action")
        amount = data.get("amount")

        with registry.locked_round(self.table_id) as round_:
            seat = registry.claim_seat(round_, self.player_id)
            try:
                round_.apply_action_and_advance(seat, action, amount)
            except ValueError as e:
                log.warning(
                    "action_rejected",
                    table_id=self.table_id, player_id=self.player_id,
                    action=action, amount=amount, reason=str(e),
                )
                await self.send(text_data=json.dumps({"error": str(e)}))
                return

            log.info(
                "action_applied",
                table_id=self.table_id, player_id=self.player_id,
                action=action, amount=amount,
                round_state=round_.current_round_state.name, pot=round_.pot,
            )

            # Broadcast the updated round state to all players at the table.
            broadcast_payload = serialize_round(round_)
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "table.message",
                    "message": broadcast_payload,
                },
            )

            if round_.seats[round_.current_turn_index].is_bot:
                bot_decide_task.delay(self.table_id, round_.seats[round_.current_turn_index].player)

    async def table_message(self, event):
        await self.send(text_data=json.dumps(event['message']))
