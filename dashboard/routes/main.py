from flask import Blueprint, render_template, jsonify
from config.shared import bot_stats # Import shared variables
from datetime import datetime
from dashboard.app import socketio  # Use the socketio instance from app.py

main_bp = Blueprint("main", __name__)

bot_start_time = datetime.now()


@main_bp.route("/")
def index():
    # Calculate uptime
    uptime = datetime.now() - bot_start_time
    uptime_str = str(uptime).split(".")[0]  # Format as HH:MM:SS

    # Fetch the latest guild count from the shared `bot_stats` dictionary
    guild_count = bot_stats.get("guild_count", 0)

    # Provide bot statistics to the template
    return render_template(
        "index.html",
        title="Moe Bot",
        guild_count=guild_count,
        uptime=uptime_str,
        year=datetime.now().year
    )


@main_bp.route("/api/stats")
def api_stats():
    # Calculate uptime
    uptime = datetime.now() - bot_start_time
    uptime_seconds = int(uptime.total_seconds())  # Uptime in seconds

    # Return bot statistics as JSON
    return jsonify(
        guild_count=bot_stats.get("guild_count", 0),
        uptime_seconds=uptime_seconds,  # Include uptime in seconds
    )


def push_guild_count_update():
    """Push guild count updates to connected clients."""
    guild_count = bot_stats.get("guild_count", 0)
    socketio.emit("update", {"guild_count": guild_count})
