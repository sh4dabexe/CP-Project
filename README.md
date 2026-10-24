# Number Duel ⚔️

A real-time, browser-based, two-player tactical number guessing game built with Python, Flask, Flask-SocketIO, and vanilla HTML/CSS/JavaScript.

---

## 🎮 Game Rules & Journey

1. **Create / Join**: Player 1 creates a room and receives a unique 4-character code and invite link. Player 2 joins via the code or link.
2. **Secret Selection**: Both players privately pick a secret integer from **1 to 100**. Secret numbers are strictly held on the server and are **never** broadcast to clients.
3. **Alternating Turns**: Player 1 takes the first turn guessing Player 2's secret number.
4. **Truthful Hints**:
   - If a guess is incorrect, the opponent whose number was guessed must provide a hint: `HIGHER` or `LOWER`.
   - The server validates the hint against the stored secret number. Untruthful hints are rejected.
   - The turn alternates only after a valid, truthful hint is registered.
5. **Victory**: The first player to guess the opponent's number wins immediately. Both secret numbers are revealed on the final scoreboard.

---

## 📂 Project Structure

```text
number-duel/
├── frontend/
│   ├── index.html       # Semantic HTML5 screens & UI components
│   ├── style.css        # Modern glassmorphism dark theme & animations
│   └── game.js          # Socket.IO client state machine & event handlers
├── backend/
│   ├── app.py           # Flask + Flask-SocketIO HTTP & WebSocket server
│   ├── game.py          # Pure Python authoritative game state & rules
│   ├── requirements.txt # Minimal Python dependencies
│   └── tests/
│       └── test_game.py # Comprehensive unit test suite
├── .env                 # Environment variables (Port, Secret Key, Firebase Key)
├── .gitignore
└── README.md
```

---

## 🚀 Quickstart

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- `pip`

### 1. Installation

**Windows (PowerShell):**
```powershell
cd "d:\Coding\CP Project\number-duel"
pip install -r backend/requirements.txt
```

**macOS / Linux:**
```bash
cd number-duel
pip install -r backend/requirements.txt
```

### 2. Run the Automated Tests

Core game rules and security constraints are verified with automated tests:
```powershell
python -m unittest discover -s backend/tests
```
Expected output:
```text
Ran 8 tests in 0.000s
OK
```

### 3. Launch the Server

```powershell
python -m backend.app
```
Or directly:
```powershell
python backend/app.py
```

Open two browser tabs or windows at:
```text
http://localhost:5000
```
- In Tab 1: Click **Create New Room**. Copy the 4-character code or invite link.
- In Tab 2: Enter the code or open the invite link.
- Duel!

---

## 📡 Socket.IO Real-Time Contracts

| Direction | Event Name | Payload Format | Description |
|---|---|---|---|
| Client → Server | `create_room` | `{ "player_name": string }` | Create a new room with host credentials |
| Client → Server | `join_room` | `{ "room_code": string, "player_name": string }` | Join an existing room as Player 2 |
| Client → Server | `choose_number` | `{ "room_code": string, "player_token": string, "number": int }` | Submit private secret number (1–100) |
| Client → Server | `guess_number` | `{ "room_code": string, "player_token": string, "guess": int }` | Active player submits guess (1–100) |
| Client → Server | `submit_hint` | `{ "room_code": string, "player_token": string, "hint": "higher" \| "lower" }` | Target player submits truthful hint |
| Client → Server | `rejoin_room` | `{ "room_code": string, "player_token": string }` | Reconnect after page refresh |
| Server → Client | `room_created` | `{ "room_code", "player_token", "player_number": 1, "player_name" }` | Private response to host |
| Server → Client | `room_joined` | `{ "room_code", "player_token", "player_number": 2, "player_name" }` | Private response to challenger |
| Server → Client | `room_rejoined`| `{ "room_code", "player_number", "player_name", "secret_number" }` | Session restored confirmation |
| Server → Client | `room_state` | *Sanitized public snapshot* | Synchronized room state sent to both players |
| Server → Client | `game_error` | `{ "message": string, "code": string }` | Validation or authorization error notification |

### Sanitized `room_state` Snapshot
```json
{
  "room_code": "K7NX",
  "status": "playing",
  "players": {
    "1": { "number": 1, "name": "Alice", "ready": true, "connected": true },
    "2": { "number": 2, "name": "Bob", "ready": true, "connected": true }
  },
  "current_turn": 1,
  "pending_hint": null,
  "history": [
    { "round": 1, "guesser": 1, "guess": 50, "hint": "higher", "result": "Alice guessed 50 — Hint: HIGHER" }
  ],
  "winner": null
}
```
*Note: Tokens and opponent secret numbers are strictly excluded from broadcasts.*

---

## 🏛️ Architecture Decision Records (ADRs)

1. **Server-Authoritative Game State**:
   - Clients render UI and submit user intents. The Python backend validates integer ranges, turn orders, hint truthfulness, and victory conditions.
2. **Opaque Token Authentication**:
   - Instead of trusting client-supplied player numbers (e.g. `player_number: 1`), the server issues high-entropy tokens (`secrets.token_hex(16)`) to identify each player.
3. **In-Memory Store for v1 Prototype**:
   - Fast, zero-dependency room tracking in a thread-safe Python dictionary. Server restarts reset active rooms.
4. **Firebase API Key Preparedness**:
   - Configured in `.env` (`Firebase_api_key`), ready for persistent matchmaking, user accounts, and Firestore leaderboards in future milestones.

---

## 🔒 Security & Quality Guarantees

- **No Secret Leakage**: Secret numbers remain server-side throughout active gameplay.
- **Truth Enforcement**: The server checks hints against secret values before accepting them.
- **Capacity Enforcement**: Rooms reject third joiners with `ROOM_FULL`.
- **Concurrency Safety**: Room state modifications are guarded by `threading.Lock`.
- **Under 1,200 Lines**: Total source code remains extremely compact and maintainable (~750 total lines across Python, HTML, CSS, and JS).
