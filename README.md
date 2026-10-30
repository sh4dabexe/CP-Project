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
