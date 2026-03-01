/**
 * Trading Arena — Socket Connection & Event Handlers
 * Manages the Socket.IO connection and incoming events.
 */

var myPlayerId = null;
var myPlayerNum = 0;
var currentState = null;
var gameMode = null;

var socket = io();

socket.on('connect', function () {
          addLog('Connected to Trading Arena server!', 'gain');
});

socket.on('disconnect', function () {
          addLog('Disconnected from server.', 'damage');
});

socket.on('player_assigned', function (data) {
          myPlayerId = data.player_id;
          myPlayerNum = data.player_num;
          document.getElementById('yourLabel').textContent = 'Player ' + myPlayerNum + ' - Your Net Worth';
          var menuEl = document.getElementById('menuScreen');
          if (menuEl) menuEl.classList.add('hidden');
          if (gameMode === 'multiplayer') {
                    var lobbyEl = document.getElementById('lobbyScreen');
                    if (lobbyEl) {
                              lobbyEl.classList.remove('hidden');
                    }
                    var lobbyMsg = document.getElementById('lobbyMsg');
                    if (lobbyMsg) {
                              lobbyMsg.textContent = 'You are Player ' + myPlayerNum + '. Waiting for opponent ...';
                    }
          }
          addLog('Assigned as Player ' + myPlayerNum, 'info');
});

socket.on('server_message', function (data) {
          addLog(data.msg, 'info');
});

socket.on('error', function (data) {
          addLog('Error: ' + data.msg, 'damage');
});

socket.on('state_update', function (state) {
          currentState = state;
          renderState(state);
});

socket.on('battle_result', function (result) {
          showBattleResult(result);
});

socket.on('game_over', function (data) {
          showAnalytics(data);
});

socket.on('game_reset', function () {
          location.reload();
});

socket.on('stock_chart_data', function (data) {
          showStockChart(data);
});

socket.on('llm_insights', function (data) {
          handleLLMInsights(data);
});