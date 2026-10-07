import re
import secrets

from django.shortcuts import redirect, render

from table import registry

# table/routing.py's WebSocket URL only matches \w+ for both segments --
# anything else (a space, a hyphen, an emoji) passes this HTTP form just
# fine, redirects into play_table(), and then fails silently at the one
# place that actually matters: the WebSocket never connects, with nothing
# on screen explaining why. Enforced here instead, with a real message,
# before that redirect ever happens.
NAME_PATTERN = re.compile(r"^\w{1,20}$")


def _validate_name(label, value):
    if not value:
        return f"Enter {label}."
    if not NAME_PATTERN.match(value):
        return f"{label.capitalize()} can only use letters, numbers, and underscores (max 20 characters)."
    return None


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

        error = _validate_name("a name", player_id)
        if error:
            return render(request, "table/create_game.html", {"error": error, "num_bots": num_bots})

        table_id = secrets.token_hex(4)
        registry.create_table(table_id, num_seats=num_bots + 1)
        return redirect("play_table", table_id=table_id, player_id=player_id)

    return render(request, "table/create_game.html", {"num_bots": 4})


def join_game(request, table_id=None):
    if request.method == "POST":
        player_id = request.POST.get("player_id", "").strip()
        posted_table_id = request.POST.get("table_id", "").strip()

        error = _validate_name("your name", player_id) or _validate_name("a table code", posted_table_id)
        if error:
            return render(request, "table/join_game.html", {"error": error, "table_id": posted_table_id})
        return redirect("play_table", table_id=posted_table_id, player_id=player_id)

    return render(request, "table/join_game.html", {"table_id": table_id or ""})


def play_table(request, table_id, player_id):
    """Minimal local dev UI -- renders play.html, which does the rest over
    the same WebSocket endpoint the engine already exposes."""
    # Reachable directly by URL, bypassing create_game()/join_game()'s own
    # validation (a hand-typed or bookmarked link) -- same \w+ reasoning as
    # there: an invalid table_id/player_id would otherwise render a page
    # whose WebSocket never connects, with no explanation why.
    if not (NAME_PATTERN.match(table_id) and NAME_PATTERN.match(player_id)):
        return redirect("lobby")
    return render(request, "table/play.html", {"table_id": table_id, "player_id": player_id})
