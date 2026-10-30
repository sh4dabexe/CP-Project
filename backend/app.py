import eventlet
eventlet.monkey_patch()

import os, secrets

from flask import Flask, send_from_directory, jsonify, request
from flask_socketio import SocketIO, emit, join_room as sock_join
from dotenv import load_dotenv
import sys
base_dir = os.path.abspath(os.path.dirname(__file__))
if base_dir not in sys.path: sys.path.insert(0, base_dir)
try:
    from game import GameManager, GameError
except ImportError:
    from backend.game import GameManager, GameError

base_dir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(base_dir, "..", ".env"))
load_dotenv(os.path.join(base_dir, "..", "..", "number-duel-spec-files", ".env"))

frontend_dir = os.path.abspath(os.path.join(base_dir, "..", "frontend"))
app = Flask(__name__, static_folder=frontend_dir, static_url_path="")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", secrets.token_hex(24))

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")
gm = GameManager()

@app.route("/")
@app.route("/join/<room_code>")
@app.route("/room/<room_code>")
def index(room_code=None):
    return send_from_directory(frontend_dir, "index.html")

@app.route("/api/health")
def health():
    return jsonify({"status": "healthy", "service": "number-duel", "firebase_configured": bool(os.getenv("Firebase_api_key"))})

@socketio.on("create_room")
def on_create(data):
    try:
        name = (data or {}).get("player_name", "Player 1")
        room, token, num = gm.create_room(name, request.sid)
        sock_join(room.code)
        emit("room_created", {"room_code": room.code, "player_token": token, "player_number": num, "player_name": name})
        socketio.emit("room_state", room.to_public_dict(), to=room.code)
    except GameError as e: emit("game_error", {"message": e.message, "code": e.code})

@socketio.on("join_room")
def on_join(data):
    try:
        code, name = (data or {}).get("room_code", ""), (data or {}).get("player_name", "Player 2")
        room, token, num = gm.join_room(code, name, request.sid)
        sock_join(room.code)
        emit("room_joined", {"room_code": room.code, "player_token": token, "player_number": num, "player_name": name})
        socketio.emit("room_state", room.to_public_dict(), to=room.code)
    except GameError as e: emit("game_error", {"message": e.message, "code": e.code})

@socketio.on("rejoin_room")
def on_rejoin(data):
    try:
        code, token = (data or {}).get("room_code", ""), (data or {}).get("player_token", "")
        room, num = gm.rejoin_room(code, token, request.sid)
        sock_join(room.code)
        emit("room_rejoined", {"room_code": room.code, "player_number": num, "player_name": room.players[num].name, "secret_number": room.players[num].secret_number})
        socketio.emit("room_state", room.to_public_dict(), to=room.code)
    except GameError as e: emit("game_error", {"message": e.message, "code": e.code})

@socketio.on("choose_number")
def on_choose(data):
    try:
        room = gm.choose_number(data.get("room_code"), data.get("player_token"), data.get("number"))
        emit("number_chosen", {"number": int(data.get("number"))})
        socketio.emit("room_state", room.to_public_dict(), to=room.code)
    except GameError as e: emit("game_error", {"message": e.message, "code": e.code})

@socketio.on("guess_number")
def on_guess(data):
    try:
        room = gm.make_guess(data.get("room_code"), data.get("player_token"), data.get("guess"))
        socketio.emit("room_state", room.to_public_dict(), to=room.code)
    except GameError as e: emit("game_error", {"message": e.message, "code": e.code})

@socketio.on("submit_hint")
def on_hint(data):
    try:
        room = gm.submit_hint(data.get("room_code"), data.get("player_token"), data.get("hint"))
        socketio.emit("room_state", room.to_public_dict(), to=room.code)
    except GameError as e: emit("game_error", {"message": e.message, "code": e.code})

@socketio.on("disconnect")
def on_disconnect():
    res = gm.handle_disconnect(request.sid)
    if res: socketio.emit("room_state", res[0].to_public_dict(), to=res[0].code)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Number Duel on http://localhost:{port}")
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
