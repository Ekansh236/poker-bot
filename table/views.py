import secrets

from django.shortcuts import redirect, render

from table import registry


def lobby(request):
    return render(request, "table/lobby.html")


def create_game(request):
    if request.method == "POST":
        player_id = request.POST.get("player_id", "").strip()
        try:
            num_bots = int(request.POST.get("num_bots", 4))
        except ValueError:
            num_bots = 4
        num_bots = max(1, min(10, num_bots))

        if not player_id:
            return render(request, "table/create_game.html", {
                "error": "Enter a name first.", "num_bots": num_bots,
            })

        table_id = secrets.token_hex(4)
        registry.create_table(table_id, num_seats=num_bots + 1)
        return redirect("play_table", table_id=table_id, player_id=player_id)

    return render(request, "table/create_game.html", {"num_bots": 4})


def join_game(request, table_id=None):
    if request.method == "POST":
        player_id = request.POST.get("player_id", "").strip()
        posted_table_id = request.POST.get("table_id", "").strip()

        if not posted_table_id or not player_id:
            return render(request, "table/join_game.html", {
                "error": "Enter both a table code and your name.",
                "table_id": posted_table_id,
            })
        return redirect("play_table", table_id=posted_table_id, player_id=player_id)

    return render(request, "table/join_game.html", {"table_id": table_id or ""})


def play_table(request, table_id, player_id):
    """Minimal local dev UI -- renders play.html, which does the rest over
    the same WebSocket endpoint the engine already exposes."""
    return render(request, "table/play.html", {"table_id": table_id, "player_id": player_id})
