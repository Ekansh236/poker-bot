from django.db import models


class Table(models.Model):
    table_id = models.CharField(primary_key=True, max_length=50)

class Hand(models.Model):
    table = models.ForeignKey(Table, on_delete=models.PROTECT)
    played_at = models.DateTimeField(auto_now_add=True)
    # Shape at creation time: [{"rank": "ACE", "suit": "Hearts"}, ...]
    board = models.JSONField()
    pot = models.IntegerField()
    # Shape at creation time: [{"player": "alice", "amount": 620}, ...]
    results = models.JSONField()
    hand_number = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["table", "hand_number"], name="unique_hand_number_per_table"),
        ]

