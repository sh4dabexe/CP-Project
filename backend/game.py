import secrets
import threading
from typing import Dict, Optional, Tuple, Any, List

class GameError(Exception):
    def __init__(self, message: str, code: str = "INVALID_ACTION"):
        super().__init__(message)
        self.message, self.code = message, code

class Player:
    def __init__(self, number: int, name: str, token: str, socket_id: Optional[str] = None):
        self.number = number
        self.name = name.strip() or f"Player {number}"
        self.token = token
        self.socket_id = socket_id
        self.secret_number: Optional[int] = None
        self.connected: bool = True

    @property
    def is_ready(self) -> bool:
        return self.secret_number is not None

class Room:
    def __init__(self, code: str):
        self.code = code
        self.status = "waiting"  # waiting, choosing, playing, finished
        self.players: Dict[int, Player] = {}
        self.current_turn: Optional[int] = None
        self.pending_hint: Optional[Dict[str, int]] = None
        self.history: List[Dict[str, Any]] = []
        self.winner: Optional[int] = None

    def get_player(self, token: str) -> Optional[Player]:
        return next((p for p in self.players.values() if p.token == token), None)

    def to_public_dict(self) -> Dict[str, Any]:
        """Safe public room snapshot; never leaks secret numbers or tokens during play."""
        data: Dict[str, Any] = {
            "room_code": self.code,
            "status": self.status,
            "players": {str(n): {"number": p.number, "name": p.name, "ready": p.is_ready, "connected": p.connected} for n, p in self.players.items()},
            "current_turn": self.current_turn,
            "pending_hint": self.pending_hint,
            "history": self.history,
            "winner": self.winner
        }
        if self.status == "finished":
            data["revealed_secrets"] = {str(n): p.secret_number for n, p in self.players.items()}
        return data

class GameManager:
    def __init__(self):
        self._rooms: Dict[str, Room] = {}
        self._lock = threading.Lock()

    def _generate_code(self) -> str:
        chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        for _ in range(100):
            code = "".join(secrets.choice(chars) for _ in range(4))
            if code not in self._rooms:
                return code
        raise GameError("Server capacity reached.", "ROOM_CAPACITY")

    def create_room(self, name: str, socket_id: Optional[str] = None) -> Tuple[Room, str, int]:
        with self._lock:
            code = self._generate_code()
            room = Room(code)
            token = secrets.token_hex(16)
            room.players[1] = Player(1, name, token, socket_id)
            self._rooms[code] = room
            return room, token, 1

    def join_room(self, code: str, name: str, socket_id: Optional[str] = None) -> Tuple[Room, str, int]:
        code = code.strip().upper()
        with self._lock:
            room = self._rooms.get(code)
            if not room:
                raise GameError(f"Room '{code}' not found.", "ROOM_NOT_FOUND")
            if len(room.players) >= 2:
                raise GameError("Room is full (max 2 players).", "ROOM_FULL")
            if room.status != "waiting":
                raise GameError("Game already in progress.", "INVALID_ROOM_STATUS")
            token = secrets.token_hex(16)
            room.players[2] = Player(2, name, token, socket_id)
            room.status = "choosing"
            return room, token, 2

    def rejoin_room(self, code: str, token: str, new_socket_id: Optional[str] = None) -> Tuple[Room, int]:
        code = code.strip().upper()
        with self._lock:
            room = self._rooms.get(code)
            if not room:
                raise GameError(f"Room '{code}' not found.", "ROOM_NOT_FOUND")
            player = room.get_player(token)
            if not player:
                raise GameError("Invalid player token.", "AUTH_FAILED")
            player.connected = True
            if new_socket_id:
                player.socket_id = new_socket_id
            return room, player.number

    def handle_disconnect(self, socket_id: str) -> Optional[Tuple[Room, int]]:
        with self._lock:
            for room in self._rooms.values():
                for p in room.players.values():
                    if p.socket_id == socket_id:
                        p.connected = False
                        return room, p.number
            return None

    def choose_number(self, code: str, token: str, val: Any) -> Room:
        num = self._validate_num(val)
        with self._lock:
            room = self._get_room(code)
            if room.status not in ("waiting", "choosing"):
                raise GameError("Match is already ongoing.", "INVALID_STATE")
            player = self._auth(room, token)
            player.secret_number = num
            if len(room.players) == 2 and all(p.is_ready for p in room.players.values()):
                room.status = "playing"
                room.current_turn = 1
            return room

    def make_guess(self, code: str, token: str, val: Any) -> Room:
        guess = self._validate_num(val)
        with self._lock:
            room = self._get_room(code)
            if room.status != "playing":
                raise GameError("Game is not active.", "INVALID_STATE")
            if room.pending_hint:
                raise GameError("Waiting for hint on previous guess.", "PENDING_HINT")
            player = self._auth(room, token)
            if room.current_turn != player.number:
                raise GameError("Not your turn to guess.", "OUT_OF_TURN")
            opp = room.players[2 if player.number == 1 else 1]
            if guess == opp.secret_number:
                room.status, room.winner = "finished", player.number
                room.history.append({"round": len(room.history) + 1, "guesser": player.number, "guess": guess, "hint": "correct"})
            else:
                room.pending_hint = {"guesser": player.number, "target": opp.number, "guess": guess}
            return room

    def submit_hint(self, code: str, token: str, hint: str) -> Room:
        hint = str(hint).strip().lower()
        if hint not in ("higher", "lower"):
            raise GameError("Hint must be 'higher' or 'lower'.", "INVALID_HINT")
        with self._lock:
            room = self._get_room(code)
            if room.status != "playing" or not room.pending_hint:
                raise GameError("No guess awaiting a hint.", "NO_PENDING_HINT")
            player = self._auth(room, token)
            pending = room.pending_hint
            if player.number != pending["target"]:
                raise GameError("Only the target secret owner provides the hint.", "WRONG_HINT_PROVIDER")
            secret, guess = player.secret_number, pending["guess"]
            if secret > guess and hint != "higher":
                raise GameError(f"Untruthful hint! {secret} is higher than {guess}.", "UNTRUTHFUL_HINT")
            if secret < guess and hint != "lower":
                raise GameError(f"Untruthful hint! {secret} is lower than {guess}.", "UNTRUTHFUL_HINT")
            room.history.append({"round": len(room.history) + 1, "guesser": pending["guesser"], "guess": guess, "hint": hint})
            room.pending_hint = None
            room.current_turn = 2 if pending["guesser"] == 1 else 1
            return room

    def get_public_state(self, code: str) -> Dict[str, Any]:
        with self._lock:
            return self._get_room(code).to_public_dict()

    def _get_room(self, code: str) -> Room:
        room = self._rooms.get(code.strip().upper())
        if not room:
            raise GameError("Room not found.", "ROOM_NOT_FOUND")
        return room

    def _auth(self, room: Room, token: str) -> Player:
        player = room.get_player(token)
        if not player:
            raise GameError("Unauthorized action.", "AUTH_FAILED")
        return player

    @staticmethod
    def _validate_num(val: Any) -> int:
        try:
            n = int(val)
        except (ValueError, TypeError):
            raise GameError("Value must be an integer.", "INVALID_INPUT")
        if n < 1 or n > 100:
            raise GameError("Number must be between 1 and 100.", "OUT_OF_RANGE")
        return n
