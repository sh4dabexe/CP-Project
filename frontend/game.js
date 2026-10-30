/**
 * Number Duel — Client State Machine & Socket.IO Controller
 */
(() => {
  'use strict';
  const state = { roomCode: null, playerToken: null, playerNumber: null, playerName: 'Player', mySecretNumber: null, currentRoomState: null };
  const $ = (id) => document.getElementById(id);
  const screens = { lobby: $('lobbyScreen'), waiting: $('waitingScreen'), choosing: $('choosingScreen'), playing: $('playingScreen'), finished: $('finishedScreen') };
  // 🔧 DEPLOYMENT CONFIG:
  // On localhost → connects to http://localhost:5000
  // On Vercel (production) → set your Render URL below
  const RENDER_URL = 'YOUR_RENDER_URL_HERE'; // e.g. 'https://number-duel-xxxx.onrender.com'
  const BACKEND_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? '' // empty string = same origin (local dev)
    : RENDER_URL;
  const socket = io(BACKEND_URL, { reconnection: true, reconnectionAttempts: 10 });


  function showScreen(name) {
    Object.keys(screens).forEach((k) => screens[k].classList.toggle('active', k === name));
  }
  function showToast(msg, type = 'info') {
    const t = document.createElement('div');
    t.className = `toast toast-${type}`;
    t.textContent = msg;
    $('toastContainer').appendChild(t);
    setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 250); }, 3500);
  }
  function saveSession() { sessionStorage.setItem('numberDuel_session', JSON.stringify(state)); }
  function loadSession() {
    try {
      const s = sessionStorage.getItem('numberDuel_session');
      if (s) { Object.assign(state, JSON.parse(s)); if ($('playerNameInput')) $('playerNameInput').value = state.playerName || 'Player'; return true; }
    } catch {}
    return false;
  }
  function clearSession() {
    sessionStorage.removeItem('numberDuel_session');
    state.roomCode = state.playerToken = state.playerNumber = state.mySecretNumber = state.currentRoomState = null;
  }

  function render(room) {
    state.currentRoomState = room;
    if (!room) return;
    const p1 = room.players['1'], p2 = room.players['2'];

    if (room.status === 'waiting') {
      showScreen('waiting');
      $('inviteLinkInput').value = `${window.location.origin}?room=${room.room_code}`;
      $('displayRoomCode').textContent = room.room_code;
      if (p1) $('p1NameDisplay').textContent = p1.name;
    } else if (room.status === 'choosing') {
      showScreen('choosing');
      if (p1) { $('chooseP1Name').textContent = p1.name; $('chooseP1State').textContent = p1.ready ? 'Locked in 🔒' : 'Picking...'; $('p1StatusPill').classList.toggle('ready', p1.ready); }
      if (p2) { $('chooseP2Name').textContent = p2.name; $('chooseP2State').textContent = p2.ready ? 'Locked in 🔒' : 'Picking...'; $('p2StatusPill').classList.toggle('ready', p2.ready); }
      const ready = (state.playerNumber === 1 && p1?.ready) || (state.playerNumber === 2 && p2?.ready);
      $('numberSelectArea').classList.toggle('hidden', ready && !!state.mySecretNumber);
      $('numberChosenConfirmed').classList.toggle('hidden', !ready || !state.mySecretNumber);
      if (state.mySecretNumber) $('confirmedSecretBadge').textContent = state.mySecretNumber;
    } else if (room.status === 'playing') {
      showScreen('playing');
      $('inGameRoomCode').textContent = room.room_code;
      const my = state.playerNumber === 1 ? p1 : p2, opp = state.playerNumber === 1 ? p2 : p1;
      $('myDisplayName').textContent = my ? my.name : `P${state.playerNumber}`;
      $('opponentDisplayName').textContent = opp ? opp.name : 'Opponent';
      $('mySecretNumber').textContent = state.mySecretNumber || '🔒';
      if ($('hintDefendSecret')) $('hintDefendSecret').textContent = state.mySecretNumber || '--';

      const isMyTurn = room.current_turn === state.playerNumber, pending = room.pending_hint;
      $('guessBox').classList.add('hidden'); $('provideHintBox').classList.add('hidden'); $('waitingForHintBox').classList.add('hidden');

      if (pending) {
        if (state.playerNumber === pending.target) {
          $('provideHintBox').classList.remove('hidden');
          $('opponentGuessValue').textContent = pending.guess;
          document.querySelectorAll('.opp-guess-ref').forEach(el => el.textContent = pending.guess);
          $('turnBanner').className = 'turn-banner my-turn'; $('turnIcon').textContent = '⚡';
          $('turnMainText').textContent = 'Hint Required!'; $('turnSubText').textContent = `Opponent guessed ${pending.guess}. Submit HIGHER or LOWER.`;
        } else {
          $('waitingForHintBox').classList.remove('hidden'); $('myLastGuessWaiting').textContent = pending.guess;
          $('turnBanner').className = 'turn-banner opponent-turn'; $('turnIcon').textContent = '⏳';
          $('turnMainText').textContent = "Waiting for Opponent's Hint"; $('turnSubText').textContent = `You guessed ${pending.guess}...`;
        }
      } else {
        if (isMyTurn) {
          $('guessBox').classList.remove('hidden'); $('turnBanner').className = 'turn-banner my-turn'; $('turnIcon').textContent = '🎯';
          $('turnMainText').textContent = 'Your Turn!'; $('turnSubText').textContent = 'Guess integer 1–100.'; $('guessInput').focus();
        } else {
          $('turnBanner').className = 'turn-banner opponent-turn'; $('turnIcon').textContent = '⏳';
          $('turnMainText').textContent = `${opp ? opp.name : 'Opponent'}'s Turn`; $('turnSubText').textContent = 'Waiting for guess...';
        }
      }
      renderHistory(room.history);
    } else if (room.status === 'finished') {
      showScreen('finished');
      const win = state.playerNumber === room.winner;
      $('victoryIcon').textContent = win ? '🏆' : '💥';
      $('victoryTitle').textContent = win ? 'Victory! You Won!' : `${room.players[String(room.winner)]?.name || 'Opponent'} Won!`;
      if (p1) $('revealP1Name').textContent = p1.name;
      if (p2) $('revealP2Name').textContent = p2.name;
      if (room.revealed_secrets) { $('revealP1Secret').textContent = room.revealed_secrets['1'] || '--'; $('revealP2Secret').textContent = room.revealed_secrets['2'] || '--'; }
      $('finalRoundsCount').textContent = (room.history || []).length;
    }
  }

  function renderHistory(history) {
    if (!history?.length) { $('duelLogStream').innerHTML = '<div class="log-empty">No guesses yet. Player 1 starts!</div>'; $('logRoundCount').textContent = '0 rounds'; return; }
    $('logRoundCount').textContent = `${history.length} round${history.length > 1 ? 's' : ''}`;
    $('duelLogStream').innerHTML = [...history].reverse().map(e => `
      <div class="log-entry">
        <div class="log-entry-left">
          <span class="round-tag">R${e.round}</span>
          <span class="log-player-name">${state.playerNumber === e.guesser ? 'You' : (state.currentRoomState?.players[String(e.guesser)]?.name || 'Player')}</span>
          <span class="log-guess-badge">Guessed ${e.guess}</span>
        </div>
        <div><span class="hint-pill ${e.hint}">${e.hint === 'correct' ? '🎯 CORRECT' : (e.hint === 'higher' ? '⬆️ HIGHER' : '⬇️ LOWER')}</span></div>
      </div>`).join('');
  }

  socket.on('connect', () => {
    $('connectionStatus').className = 'badge badge-online'; $('connectionStatus').innerHTML = '<span class="dot"></span> Connected';
    if (state.roomCode && state.playerToken) socket.emit('rejoin_room', { room_code: state.roomCode, player_token: state.playerToken });
  });
  socket.on('disconnect', () => { $('connectionStatus').className = 'badge badge-offline'; $('connectionStatus').innerHTML = '<span class="dot"></span> Disconnected'; });
  socket.on('room_created', (d) => { Object.assign(state, { roomCode: d.room_code, playerToken: d.player_token, playerNumber: d.player_number, playerName: d.player_name }); saveSession(); showToast(`Room ${d.room_code} created!`, 'success'); });
  socket.on('room_joined', (d) => { Object.assign(state, { roomCode: d.room_code, playerToken: d.player_token, playerNumber: d.player_number, playerName: d.player_name }); saveSession(); showToast(`Joined Room ${d.room_code}!`, 'success'); });
  socket.on('room_rejoined', (d) => { state.playerNumber = d.player_number; state.playerName = d.player_name; if (d.secret_number) state.mySecretNumber = d.secret_number; saveSession(); showToast(`Reconnected!`, 'success'); });
  socket.on('room_state', render);
  socket.on('number_chosen', (d) => { state.mySecretNumber = d.number; saveSession(); showToast(`Secret ${d.number} locked in!`, 'success'); $('confirmedSecretBadge').textContent = d.number; $('mySecretNumber').textContent = d.number; });
  socket.on('game_error', (d) => showToast(d.message || 'Game error', 'error'));

  $('createRoomBtn').addEventListener('click', () => { const n = $('playerNameInput').value.trim() || 'Player 1'; state.playerName = n; socket.emit('create_room', { player_name: n }); });
  $('joinRoomBtn').addEventListener('click', () => {
    const c = $('roomCodeInput').value.trim().toUpperCase(), n = $('playerNameInput').value.trim() || 'Player 2';
    if (c.length !== 4) return showToast('Enter 4-character code.', 'warning');
    state.playerName = n; socket.emit('join_room', { room_code: c, player_name: n });
  });
  $('copyInviteBtn').addEventListener('click', async () => {
    try { await navigator.clipboard.writeText($('inviteLinkInput').value); } catch { $('inviteLinkInput').select(); document.execCommand('copy'); }
    $('copyBtnText').textContent = '✅ Copied!'; showToast('Link copied!', 'success'); setTimeout(() => $('copyBtnText').textContent = '📋 Copy Link', 2000);
  });
  const toLobby = () => { clearSession(); showScreen('lobby'); window.history.pushState({}, '', window.location.pathname); };
  $('leaveRoomBtn').addEventListener('click', toLobby); $('playAgainBtn').addEventListener('click', toLobby);
  $('quickRandomBtn').addEventListener('click', () => { $('secretNumberInput').value = Math.floor(Math.random() * 100) + 1; });
  $('confirmSecretBtn').addEventListener('click', () => {
    const n = parseInt($('secretNumberInput').value, 10);
    if (isNaN(n) || n < 1 || n > 100) return showToast('Choose integer 1–100.', 'warning');
    socket.emit('choose_number', { room_code: state.roomCode, player_token: state.playerToken, number: n });
  });
  const submitGuess = () => {
    const g = parseInt($('guessInput').value, 10);
    if (isNaN(g) || g < 1 || g > 100) return showToast('Guess integer 1–100.', 'warning');
    socket.emit('guess_number', { room_code: state.roomCode, player_token: state.playerToken, guess: g });
    $('guessInput').value = '';
  };
  $('submitGuessBtn').addEventListener('click', submitGuess);
  $('guessInput').addEventListener('keydown', (e) => { if (e.key === 'Enter') submitGuess(); });
  $('hintHigherBtn').addEventListener('click', () => socket.emit('submit_hint', { room_code: state.roomCode, player_token: state.playerToken, hint: 'higher' }));
  $('hintLowerBtn').addEventListener('click', () => socket.emit('submit_hint', { room_code: state.roomCode, player_token: state.playerToken, hint: 'lower' }));

  loadSession();
  const urlParam = new URLSearchParams(window.location.search).get('room') || window.location.pathname.split('/')[2];
  if (urlParam) $('roomCodeInput').value = urlParam.toUpperCase();
})();
