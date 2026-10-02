from django.conf import settings
from django.db import models

class Transaction(models.Model):
    # Fields are declared directly on the class body -- Django's ModelBase
    # metaclass turns each models.Field instance into a column at class
    # definition time, and generates __init__ for you.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="transactions",
        on_delete=models.PROTECT,   # decided: can't delete a User with transaction history
    )
    amount = models.IntegerField()  # decided: signed (+credit, -debit), not float
    created_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=50)
    idempotency_key = models.CharField(max_length=100, unique=True)
