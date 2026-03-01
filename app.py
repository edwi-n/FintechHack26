"""
Trading Arena — Strategic Stock Battle
====================================
Two-player strategy game where players manage stock portfolios and deploy
derivatives (Puts / Calls) to attack opponents and defend their Net Worth.

Entry point: creates Flask app, registers events, loads data, and starts the server.
"""

from flask import Flask
from flask_socketio import SocketIO

from server.stock_data import load_stock_data
from server.events import register_events

# ──────────────────────────────────────────────
# Flask / SocketIO setup
# ──────────────────────────────────────────────
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Register all Socket.IO and HTTP route handlers
register_events(app, socketio)

# ──────────────────────────────────────────────
# Startup
# ──────────────────────────────────────────────
if __name__ == "__main__":
    load_stock_data()
    print("[boot] Starting Trading Arena on http://localhost:5000")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
