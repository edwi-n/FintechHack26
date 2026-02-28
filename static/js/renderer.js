/**
 * Trading Arena — Renderer
 * =========================
 * All DOM rendering functions for the game UI.
 */

/* global currentState, requestStockChart, buyStock, setCardAction,
          toggleAttackPut, endBuyPhase, confirmActions */

function renderState(s) {
          var badge = document.getElementById('phaseBadge');
          badge.textContent = s.phase.toUpperCase();
          badge.className = 'phase-badge ' + s.phase;
          document.getElementById('roundInfo').textContent =
                    s.phase === 'lobby'
                              ? '-'
                              : 'Round ' + s.round + ' / ' + s.max_rounds +
                              (s.current_date ? '  |  Market Date: ' + s.current_date : '');
          updateNW('yourNW', s.net_worth);
          updateNW('oppNW', s.opponent_nw);

          if (s.phase === 'lobby') {
                    document.getElementById('lobbyScreen').classList.remove('hidden');
                    document.getElementById('gameBoard').classList.add('hidden');
          } else {
                    document.getElementById('menuScreen').classList.add('hidden');
                    document.getElementById('lobbyScreen').classList.add('hidden');
                    document.getElementById('gameBoard').classList.remove('hidden');
          }
          renderHand(s.hand, s.phase);
          renderBench(s.bench, s.phase, s.card_actions, s.ready);
          renderArena(s);
          renderOpponentBench(s.opponent_bench, s.phase, s.attack_puts, s.ready);
          renderActions(s);
}

function updateNW(id, value) {
          var el = document.getElementById(id);
          el.textContent = '\u00A3' + value.toLocaleString('en-GB', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
          });
          if (value < 0) el.style.color = 'var(--red)';
          else if (value >= 100000) el.style.color = 'var(--green)';
          else el.style.color = 'var(--gold)';
}

function renderHand(hand, phase) {
          var grid = document.getElementById('handGrid');
          if (!hand || hand.length === 0) {
                    grid.innerHTML = '<div class="empty-state">No cards in hand</div>';
                    return;
          }
          grid.innerHTML = hand.map(function (card, i) {
                    return '<div class="stock-card" onclick="requestStockChart(\'' + card.ticker + '\', ' + (card.start_idx || 0) + ')">' +
                              '<div class="ticker">' + card.ticker + '</div>' +
                              '<div class="price">\u00A3' + card.s0.toFixed(2) + '</div>' +
                              '<div class="meta">' + (card.date_start || '') + '</div>' +
                              '<div class="premiums">Call: \u00A3' + card.call_premium.toFixed(2) + '<br>Put: \u00A3' + card.put_premium.toFixed(2) + '</div>' +
                              (phase === 'buy' ? '<button class="card-btn btn-primary" onclick="event.stopPropagation(); buyStock(' + i + ')">Buy Card</button>' : '') +
                              '</div>';
          }).join('');
}

function renderBench(bench, phase, cardActions, ready) {
          var grid = document.getElementById('benchGrid');
          if (!bench || bench.length === 0) {
                    grid.innerHTML = '<div class="empty-state">No stocks on bench</div>';
                    return;
          }
          var isAction = phase === 'action' && !ready;
          grid.innerHTML = bench.map(function (card, i) {
                    var action = cardActions[String(i)] || null;
                    var hasAction = action !== null;
                    var html = '<div class="stock-card' + (hasAction ? ' has-action' : '') + '" ' +
                              'onclick="requestStockChart(\'' + card.ticker + '\', ' + (card.start_idx || 0) + ')">' +
                              '<div class="ticker">' + card.ticker + '</div>' +
                              '<div class="price">\u00A3' + card.s0.toFixed(2) + '</div>' +
                              '<div class="meta">' + (card.date_start || '') + '</div>' +
                              '<div class="premiums">Call: \u00A3' + card.call_premium.toFixed(2) + '<br>Put: \u00A3' + card.put_premium.toFixed(2) + '</div>';

                    if (hasAction) {
                              var label = action.replace('_', ' ').toUpperCase();
                              html += '<div class="action-badge ' + action + '">' + label + '</div>';
                    }

                    if (isAction) {
                              html += '<div class="card-action-row" onclick="event.stopPropagation()">';
                              if (action !== 'place') html += '<button class="btn-place" onclick="setCardAction(' + i + ', \'place\')" title="Place">&#9876;</button>';
                              if (action !== 'defense_put') html += '<button class="btn-defense" onclick="setCardAction(' + i + ', \'defense_put\')" title="Defense Put">&#128737;</button>';
                              if (action !== 'call') html += '<button class="btn-call" onclick="setCardAction(' + i + ', \'call\')" title="Call">&#128200;</button>';
                              if (hasAction) html += '<button class="btn-clear" onclick="setCardAction(' + i + ', null)" title="Clear">&#10005;</button>';
                              html += '</div>';
                    }

                    html += '</div>';
                    return html;
          }).join('');
}

function renderArena(s) {
          var arenaInfo = document.getElementById('yourArenaCard');
          var oppArenaInfo = document.getElementById('oppArenaCard');

          // Your actions summary
          var actions = s.card_actions || {};
          var attacks = s.attack_puts || [];
          var keys = Object.keys(actions);
          if (keys.length === 0 && attacks.length === 0) {
                    arenaInfo.innerHTML = '<span style="color:var(--muted)">No actions assigned</span>';
          } else {
                    var lines = [];
                    keys.forEach(function (idx) {
                              var card = s.bench[parseInt(idx)];
                              if (card) lines.push('<div class="arena-item">' + actions[idx].replace('_', ' ').toUpperCase() + ': ' + card.ticker + ' (\u00A3' + card.s0.toFixed(2) + ')</div>');
                    });
                    attacks.forEach(function (id) {
                              var opp = s.opponent_bench.find(function (c) { return c.id === id; });
                              if (opp) lines.push('<div class="arena-item" style="color:var(--red)">ATTACK PUT: ' + opp.ticker + ' (\u00A3' + opp.s0.toFixed(2) + ')</div>');
                    });
                    arenaInfo.innerHTML = '<div class="arena-summary">' + lines.join('') + '</div>';
          }

          // Opponent
          if (s.opponent_ready) {
                    oppArenaInfo.innerHTML = '<span style="color:var(--gold)">Actions locked in! Waiting for battle...</span>';
          } else {
                    oppArenaInfo.innerHTML = '<span style="color:var(--muted)">Deciding...</span>';
          }
}

function renderOpponentBench(bench, phase, attackPuts, ready) {
          var grid = document.getElementById('oppBenchGrid');
          if (!bench || bench.length === 0) {
                    grid.innerHTML = '<div class="empty-state">Opponent has no stocks</div>';
                    return;
          }
          var isAction = phase === 'action' && !ready;
          grid.innerHTML = bench.map(function (c) {
                    var isTargeted = attackPuts && attackPuts.indexOf(c.id) !== -1;
                    var html = '<div class="stock-card' + (isTargeted ? ' has-attack' : '') + '" ' +
                              'onclick="requestStockChart(\'' + c.ticker + '\', ' + (c.start_idx || 0) + ')">' +
                              '<div class="ticker">' + c.ticker + '</div>' +
                              '<div class="price">\u00A3' + c.s0.toFixed(2) + '</div>' +
                              '<div class="premiums">Put premium: \u00A3' + c.put_premium.toFixed(2) + '</div>';

                    if (isTargeted) {
                              html += '<div class="action-badge attack_put">ATTACK PUT</div>';
                    }

                    if (isAction) {
                              html += '<div class="card-action-row" onclick="event.stopPropagation()">';
                              if (isTargeted) {
                                        html += '<button class="btn-clear" onclick="toggleAttackPut(\'' + c.id + '\')" title="Cancel Attack Put">Cancel &#128165;</button>';
                              } else {
                                        html += '<button class="btn-attack" onclick="toggleAttackPut(\'' + c.id + '\')" title="Attack Put">&#128165; Attack Put</button>';
                              }
                              html += '</div>';
                    }

                    html += '</div>';
                    return html;
          }).join('');
}

function renderActions(s) {
          var title = document.getElementById('actionTitle');
          var content = document.getElementById('actionContent');

          if (s.phase === 'buy') {
                    title.textContent = 'Buy Phase';
                    content.innerHTML = '<p style="color:var(--muted);font-size:0.82rem;margin-bottom:12px;">Click <strong>Buy Card</strong> on cards in your hand. Cost: 5% of stock price.</p>' +
                              '<button class="btn-ready" onclick="endBuyPhase()"' + (s.ready ? ' disabled' : '') + '>' +
                              (s.ready ? 'Waiting for opponent...' : 'Done Buying \u2192 Ready') + '</button>';
          } else if (s.phase === 'action') {
                    title.textContent = 'Action Phase';
                    if (s.ready) {
                              content.innerHTML = '<p style="color:var(--gold);font-size:0.9rem;">Actions confirmed! Waiting for opponent...</p>';
                    } else {
                              var numActions = Object.keys(s.card_actions).length + (s.attack_puts ? s.attack_puts.length : 0);
                              content.innerHTML = '<p style="color:var(--muted);font-size:0.82rem;margin-bottom:12px;">' +
                                        'Assign actions to each bench card using the buttons on each card. ' +
                                        'Attack Put buttons are on opponent\'s cards.' +
                                        '</p>' +
                                        '<p style="color:var(--text);font-size:0.85rem;margin-bottom:12px;">' +
                                        '<strong>' + numActions + '</strong> action(s) assigned' +
                                        '</p>' +
                                        '<button class="btn-ready" onclick="confirmActions()">Confirm All Actions \u2192 Ready</button>';
                    }
          } else if (s.phase === 'battle') {
                    title.textContent = 'Battle Phase';
                    content.innerHTML = '<p style="color:var(--gold);font-size:0.9rem;">Resolving battle...</p>';
          } else {
                    title.textContent = 'Actions';
                    content.innerHTML = '';
          }
}