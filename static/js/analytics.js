/**
 * Trading Arena — Analytics & Battle Results
 * End-of-game analytics overlay and per-round battle log.
 */

function showBattleResult(result) {
          var myData = result[myPlayerId];
          var oppId = myPlayerId === 'player_1' ? 'player_2' : 'player_1';
          var oppData = result[oppId];
          addLog('--- Round ' + result.round + ' Battle Results ---', 'info');
          result.events.forEach(function (evt) {
                    var cls = evt.indexOf('damage') !== -1 ? 'damage'
                              : evt.indexOf('Recovered') !== -1 ? 'gain'
                                        : 'info';
                    addLog(evt, cls);
          });
          addLog('Your NW: \u00A3' + myData.new_nw.toLocaleString(), myData.new_nw >= 100000 ? 'gain' : 'damage');
          addLog('Opponent NW: \u00A3' + oppData.new_nw.toLocaleString(), oppData.new_nw >= 100000 ? 'gain' : 'damage');
}

function showAnalytics(data) {
          document.getElementById('analyticsOverlay').classList.remove('hidden');
          var banner = document.getElementById('winnerBanner');
          if (data.winner === myPlayerId) {
                    banner.textContent = '\uD83C\uDFC6 YOU WIN! \uD83C\uDFC6';
                    banner.style.color = 'var(--gold)';
          } else if (data.winner === 'draw') {
                    banner.textContent = "It's a Draw!";
                    banner.style.color = 'var(--muted)';
          } else {
                    banner.textContent = 'You Lost. Better luck next time!';
                    banner.style.color = 'var(--red)';
          }
          var oppId = myPlayerId === 'player_1' ? 'player_2' : 'player_1';
          renderPlayerStats('p1Stats', data.analytics[myPlayerId]);
          document.getElementById('p1StatsTitle').textContent = 'You (Player ' + myPlayerNum + ')';
          renderPlayerStats('p2Stats', data.analytics[oppId]);
          document.getElementById('p2StatsTitle').textContent = 'Opponent';
          renderNWChart(data.analytics[myPlayerId].nw_history, data.analytics[oppId].nw_history);
}

function renderPlayerStats(id, a) {
          var p = a.total_profit;
          document.getElementById(id).innerHTML =
                    '<div class="stat-card"><div class="stat-label">Total Profit</div><div class="stat-value" style="color:' + (p >= 0 ? 'var(--green)' : 'var(--red)') + '">\u00A3' + p.toLocaleString('en-GB', { minimumFractionDigits: 2 }) + '</div></div>' +
                    '<div class="stat-card"><div class="stat-label">Options Win Rate</div><div class="stat-value" style="color:var(--accent)">' + a.options_win_rate + '%</div></div>' +
                    '<div class="stat-card"><div class="stat-label">Max Drawdown</div><div class="stat-value" style="color:var(--red)">-\u00A3' + a.max_drawdown.toLocaleString('en-GB', { minimumFractionDigits: 2 }) + '</div></div>' +
                    '<div class="stat-card"><div class="stat-label">Final NW</div><div class="stat-value" style="color:' + (a.final_nw >= 100000 ? 'var(--green)' : 'var(--gold)') + '">\u00A3' + a.final_nw.toLocaleString('en-GB', { minimumFractionDigits: 2 }) + '</div></div>';
}
