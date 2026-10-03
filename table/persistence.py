from django.contrib.auth.models import User

from accounts.models import Transaction
from poker_engine.round import Round
from table.models import Hand, Table


def persist_hand_result(table_id: str, round_: Round) -> None:
    """Write a Hand row and winner Transaction row(s) for a hand that just
    resolved (round_.last_showdown is set). Safe to call more than once for
    the same hand -- both Hand (keyed on table+hand_number) and Transaction
    (keyed on idempotency_key) get_or_create() against their unique
    constraints, so a retried caller can't create duplicates or double
    -credit a winner.
    """
    table = Table.objects.get_or_create(table_id=table_id)[0]
    hand, _ = Hand.objects.get_or_create(
        table=table,
        hand_number=round_.last_showdown["hand_id"],
        defaults={
            "board": round_.last_showdown["board"],
            "pot": sum(r["amount"] for r in round_.last_showdown["results"]),
            "results": round_.last_showdown["results"],
        },
    )

    for result in round_.last_showdown["results"]:
        seat = next(s for s in round_.seats if s.player == result["player"])
        if seat.is_bot:
            continue  # no User account to credit

        user, _ = User.objects.get_or_create(username=result["player"])
        Transaction.objects.get_or_create(
            idempotency_key=f"hand:{round_.last_showdown['hand_id']}:{result['player']}",
            defaults={
                "user": user,
                "amount": result["amount"],
                "reason": "hand_settlement",
            },
        )
