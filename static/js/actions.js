/**
 * Trading Arena — User Actions
 * Functions triggered by player button clicks.
 */

function buyStock(i) {
          playSound('buy');
          socket.emit('buy_stock', { player_id: myPlayerId, card_index: i });
}

function endBuyPhase() {
          playSound('confirm');
          socket.emit('end_buy_phase', { player_id: myPlayerId });
}

function setCardAction(cardIndex, action) {
          if (action) playSound('buy');
          socket.emit('set_card_action', { player_id: myPlayerId, card_index: cardIndex, action: action });
}

function toggleAttackPut(cardId) {
          playSound('damage');
          socket.emit('toggle_attack_put', { player_id: myPlayerId, target_card_id: cardId });
}

function confirmActions() {
          playSound('confirm');
          socket.emit('confirm_actions', { player_id: myPlayerId });
}

function restartGame() {
          socket.emit('restart_game');
}
