from django.shortcuts import render


def play_table(request, table_id, player_id):
    """Minimal local dev UI -- renders play.html, which does the rest over
    the same WebSocket endpoint the engine already exposes."""
    return render(request, "table/play.html", {"table_id": table_id, "player_id": player_id})
