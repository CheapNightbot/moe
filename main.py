from bot.main import run_bot_with_event, client  # Import directly from bot.main
from dashboard.app import app, socketio  # Import socketio from app.py
from config.shared import bot_stats
import multiprocessing
from waitress import serve

# Create an event to signal when the bot is ready
bot_ready_event = multiprocessing.Event()


def run_dashboard():
    from dashboard.routes.main import bot_stats as dashboard_stats

    # Wait for the bot to signal readiness
    bot_ready_event.wait()

    # Use the shared `bot_stats` dictionary
    dashboard_stats.clear()
    dashboard_stats.update(bot_stats)

    # Use Waitress to serve the Flask app securely
    serve(app, host="0.0.0.0", port=10000, threads=4)  # Use 4 threads for concurrency


if __name__ == "__main__":
    # Run bot and dashboard in parallel
    bot_process = multiprocessing.Process(
        target=run_bot_with_event, args=(bot_ready_event, client)
    )
    dashboard_process = multiprocessing.Process(target=run_dashboard)

    bot_process.start()
    dashboard_process.start()

    bot_process.join()
    dashboard_process.join()
