/**
 * Trading Arena — User Actions
 * Functions triggered by player button clicks.
 */

function selectMode(mode) {
          gameMode = mode;
          socket.emit('select_mode', { mode: mode });
}

function buyStock(i) {
          socket.emit('buy_stock', { player_id: myPlayerId, card_index: i });
}

function endBuyPhase() {
          socket.emit('end_buy_phase', { player_id: myPlayerId });
}

function setCardAction(cardIndex, action) {
          socket.emit('set_card_action', { player_id: myPlayerId, card_index: cardIndex, action: action });
}

function toggleAttackPut(cardId) {
          socket.emit('toggle_attack_put', { player_id: myPlayerId, target_card_id: cardId });
}

function confirmActions() {
          socket.emit('confirm_actions', { player_id: myPlayerId });
}

function restartGame() {
          socket.emit('restart_game');
}