from django.contrib import admin

from accounts.models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "reason", "idempotency_key", "created_at")
    list_filter = ("reason",)
    search_fields = ("user__username", "idempotency_key")
