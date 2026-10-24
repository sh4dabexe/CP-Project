import unittest
from backend.game import GameManager, GameError

class TestNumberDuel(unittest.TestCase):
    def setUp(self):
        self.gm = GameManager()

    def test_room_lifecycle_and_capacity(self):
        r, t1, n1 = self.gm.create_room("Alice", "s1")
        self.assertEqual((n1, r.status, len(r.players)), (1, "waiting", 1))
        r2, t2, n2 = self.gm.join_room(r.code, "Bob", "s2")
        self.assertEqual((n2, r2.status, len(r2.players)), (2, "choosing", 2))
        with self.assertRaises(GameError) as ctx:
            self.gm.join_room(r.code, "Charlie")
        self.assertEqual(ctx.exception.code, "ROOM_FULL")

    def test_number_validation_and_readiness(self):
        r, t1, _ = self.gm.create_room("Alice")
        _, t2, _ = self.gm.join_room(r.code, "Bob")
        for bad in (0, 101, "abc"):
            with self.assertRaises(GameError):
                self.gm.choose_number(r.code, t1, bad)
        self.gm.choose_number(r.code, t1, 42)
        self.assertEqual(r.status, "choosing")
        self.gm.choose_number(r.code, t2, 85)
        self.assertEqual((r.status, r.current_turn), ("playing", 1))

    def test_guessing_and_turn_enforcement(self):
        r, t1, _ = self.gm.create_room("Alice")
        _, t2, _ = self.gm.join_room(r.code, "Bob")
        self.gm.choose_number(r.code, t1, 42)
        self.gm.choose_number(r.code, t2, 85)
        # Player 2 out of turn
        with self.assertRaises(GameError) as ctx:
            self.gm.make_guess(r.code, t2, 50)
        self.assertEqual(ctx.exception.code, "OUT_OF_TURN")
        # Player 1 wrong guess
        self.gm.make_guess(r.code, t1, 50)
        self.assertIsNotNone(r.pending_hint)
        with self.assertRaises(GameError):
            self.gm.make_guess(r.code, t1, 60)

    def test_truthful_hint_enforcement(self):
        r, t1, _ = self.gm.create_room("Alice")
        _, t2, _ = self.gm.join_room(r.code, "Bob")
        self.gm.choose_number(r.code, t1, 42)
        self.gm.choose_number(r.code, t2, 85)
        self.gm.make_guess(r.code, t1, 50) # Bob's secret is 85 -> higher
        with self.assertRaises(GameError) as ctx:
            self.gm.submit_hint(r.code, t1, "higher") # Alice can't hint
        self.assertEqual(ctx.exception.code, "WRONG_HINT_PROVIDER")
        with self.assertRaises(GameError) as ctx:
            self.gm.submit_hint(r.code, t2, "lower") # Bob lies
        self.assertEqual(ctx.exception.code, "UNTRUTHFUL_HINT")
        self.gm.submit_hint(r.code, t2, "higher") # Truthful
        self.assertEqual((r.pending_hint, r.current_turn), (None, 2))

    def test_winning_guess_and_secret_privacy(self):
        r, t1, _ = self.gm.create_room("Alice")
        _, t2, _ = self.gm.join_room(r.code, "Bob")
        self.gm.choose_number(r.code, t1, 42)
        self.gm.choose_number(r.code, t2, 85)
        # Privacy check while playing
        pub = self.gm.get_public_state(r.code)
        self.assertNotIn("42", str(pub))
        self.assertNotIn("85", str(pub))
        self.assertNotIn(t1, str(pub))
        # Winning guess
        self.gm.make_guess(r.code, t1, 85)
        self.assertEqual((r.status, r.winner), ("finished", 1))

    def test_reconnect(self):
        r, t1, _ = self.gm.create_room("Alice", "s1")
        self.gm.handle_disconnect("s1")
        self.assertFalse(r.players[1].connected)
        rejoined, num = self.gm.rejoin_room(r.code, t1, "s2")
        self.assertEqual((num, rejoined.players[1].connected), (1, True))

if __name__ == "__main__":
    unittest.main()
