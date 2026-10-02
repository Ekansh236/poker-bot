from django.contrib import admin

from table.models import Hand, Table


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ("table_id",)


@admin.register(Hand)
class HandAdmin(admin.ModelAdmin):
    list_display = ("table", "played_at", "pot")
    list_filter = ("table",)
