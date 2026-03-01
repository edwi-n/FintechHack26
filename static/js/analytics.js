/**
 * Trading Arena — Analytics & Battle Results
 * End-of-game analytics overlay, animated battle results, and LLM insights.
 */

/* ── Sound Effects (Web Audio API) ── */
var audioCtx = null;
function getAudioCtx() {
          if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
          return audioCtx;
}

function playSound(type) {
          try {
                    var ctx = getAudioCtx();
                    var osc = ctx.createOscillator();
                    var gain = ctx.createGain();
                    osc.connect(gain);
                    gain.connect(ctx.destination);

                    if (type === 'damage') {
                              osc.type = 'sawtooth';
                              osc.frequency.setValueAtTime(200, ctx.currentTime);
                              osc.frequency.exponentialRampToValueAtTime(80, ctx.currentTime + 0.3);
                              gain.gain.setValueAtTime(0.15, ctx.currentTime);
                              gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
                              osc.start(ctx.currentTime);
                              osc.stop(ctx.currentTime + 0.3);
                    } else if (type === 'gain') {
                              osc.type = 'sine';
                              osc.frequency.setValueAtTime(400, ctx.currentTime);
                              osc.frequency.exponentialRampToValueAtTime(800, ctx.currentTime + 0.25);
                              gain.gain.setValueAtTime(0.12, ctx.currentTime);
                              gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
                              osc.start(ctx.currentTime);
                              osc.stop(ctx.currentTime + 0.25);
                    } else if (type === 'critical') {
                              osc.type = 'square';
                              osc.frequency.setValueAtTime(150, ctx.currentTime);
                              osc.frequency.exponentialRampToValueAtTime(50, ctx.currentTime + 0.5);
                              gain.gain.setValueAtTime(0.2, ctx.currentTime);
                              gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5);
                              osc.start(ctx.currentTime);
                              osc.stop(ctx.currentTime + 0.5);
                              // Second hit
                              var osc2 = ctx.createOscillator();
                              var gain2 = ctx.createGain();
                              osc2.connect(gain2);
                              gain2.connect(ctx.destination);
                              osc2.type = 'sawtooth';
                              osc2.frequency.setValueAtTime(100, ctx.currentTime + 0.15);
                              osc2.frequency.exponentialRampToValueAtTime(40, ctx.currentTime + 0.6);
                              gain2.gain.setValueAtTime(0.18, ctx.currentTime + 0.15);
                              gain2.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
                              osc2.start(ctx.currentTime + 0.15);
                              osc2.stop(ctx.currentTime + 0.6);
                    } else if (type === 'victory') {
                              var notes = [523, 659, 784, 1047];
                              notes.forEach(function(freq, i) {
                                        var o = ctx.createOscillator();
                                        var g = ctx.createGain();
                                        o.connect(g);
                                        g.connect(ctx.destination);
                                        o.type = 'sine';
                                        o.frequency.setValueAtTime(freq, ctx.currentTime + i * 0.15);
                                        g.gain.setValueAtTime(0.1, ctx.currentTime + i * 0.15);
                                        g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.15 + 0.4);
                                        o.start(ctx.currentTime + i * 0.15);
                                        o.stop(ctx.currentTime + i * 0.15 + 0.4);
                              });
                    } else if (type === 'defeat') {
                              osc.type = 'sine';
                              osc.frequency.setValueAtTime(400, ctx.currentTime);
                              osc.frequency.exponentialRampToValueAtTime(150, ctx.currentTime + 0.6);
                              gain.gain.setValueAtTime(0.12, ctx.currentTime);
                              gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
                              osc.start(ctx.currentTime);
                              osc.stop(ctx.currentTime + 0.6);
                    } else if (type === 'buy') {
                              osc.type = 'sine';
                              osc.frequency.setValueAtTime(600, ctx.currentTime);
                              osc.frequency.exponentialRampToValueAtTime(900, ctx.currentTime + 0.1);
                              gain.gain.setValueAtTime(0.08, ctx.currentTime);
                              gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.15);
                              osc.start(ctx.currentTime);
                              osc.stop(ctx.currentTime + 0.15);
                    } else if (type === 'confirm') {
                              osc.type = 'sine';
                              osc.frequency.setValueAtTime(500, ctx.currentTime);
                              osc.frequency.setValueAtTime(700, ctx.currentTime + 0.1);
                              gain.gain.setValueAtTime(0.1, ctx.currentTime);
                              gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2);
                              osc.start(ctx.currentTime);
                              osc.stop(ctx.currentTime + 0.2);
                    }
          } catch (e) { /* Audio not supported */ }
}

/* ── Animated number counter ── */
function animateValue(element, start, end, duration, prefix) {
          prefix = prefix || '\u00A3';
          var startTime = null;
          var absStart = start;
          var absEnd = end;
          function step(timestamp) {
                    if (!startTime) startTime = timestamp;
                    var progress = Math.min((timestamp - startTime) / duration, 1);
                    // Ease out cubic
                    var eased = 1 - Math.pow(1 - progress, 3);
                    var current = absStart + (absEnd - absStart) * eased;
                    element.textContent = prefix + current.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                    if (progress < 1) {
                              requestAnimationFrame(step);
                    }
          }
          requestAnimationFrame(step);
}

/* ── Battle Result Overlay (animated, darkened screen) ── */
function showBattleResult(result) {
          var myData = result[myPlayerId];
          var oppId = myPlayerId === 'player_1' ? 'player_2' : 'player_1';
          var oppData = result[oppId];

          // Still log events to battle log
          addLog('--- Round ' + result.round + ' Battle Results ---', 'info');
          result.events.forEach(function (evt) {
                    var cls = evt.indexOf('damage') !== -1 ? 'damage'
                              : evt.indexOf('Recovered') !== -1 ? 'gain'
                                        : 'info';
                    addLog(evt, cls);
          });

          // Show the animated overlay
          var overlay = document.getElementById('battleOverlay');
          overlay.classList.remove('hidden');

          document.getElementById('battleTitle').textContent = 'ROUND ' + result.round + ' RESULTS';

          // Animate net worth values
          var myPrevNW = myData.new_nw - myData.arena_delta - myData.bench_omega + myData.inflation;
          var oppPrevNW = oppData.new_nw - oppData.arena_delta - oppData.bench_omega + oppData.inflation;

          var myNWEl = document.getElementById('battleYourNWValue');
          var oppNWEl = document.getElementById('battleOppNWValue');

          myNWEl.textContent = '\u00A3' + myPrevNW.toLocaleString('en-GB', { minimumFractionDigits: 2 });
          oppNWEl.textContent = '\u00A3' + oppPrevNW.toLocaleString('en-GB', { minimumFractionDigits: 2 });

          // Start NW animation after a brief delay
          setTimeout(function() {
                    animateValue(myNWEl, myPrevNW, myData.new_nw, 1500);
                    animateValue(oppNWEl, oppPrevNW, oppData.new_nw, 1500);

                    // Color
                    var myChange = myData.new_nw - myPrevNW;
                    var oppChange = oppData.new_nw - oppPrevNW;
                    myNWEl.style.color = myChange >= 0 ? 'var(--green)' : 'var(--red)';
                    oppNWEl.style.color = oppChange >= 0 ? 'var(--green)' : 'var(--red)';

                    // Delta badges
                    var myDeltaEl = document.getElementById('battleYourDelta');
                    var oppDeltaEl = document.getElementById('battleOppDelta');
                    myDeltaEl.textContent = (myChange >= 0 ? '+' : '') + '\u00A3' + myChange.toLocaleString('en-GB', { minimumFractionDigits: 2 });
                    myDeltaEl.className = 'battle-nw-delta ' + (myChange >= 0 ? 'positive' : 'negative');
                    oppDeltaEl.textContent = (oppChange >= 0 ? '+' : '') + '\u00A3' + oppChange.toLocaleString('en-GB', { minimumFractionDigits: 2 });
                    oppDeltaEl.className = 'battle-nw-delta ' + (oppChange >= 0 ? 'positive' : 'negative');

                    // Sound
                    if (myChange > 0) playSound('gain');
                    else if (myChange < 0) playSound('damage');
          }, 500);

          // Show events one by one with animation
          var eventsEl = document.getElementById('battleEvents');
          eventsEl.innerHTML = '';
          var filteredEvents = result.events.filter(function(e) {
                    return e.indexOf('HOLD') === -1;
          });
          filteredEvents.forEach(function(evt, i) {
                    setTimeout(function() {
                              var div = document.createElement('div');
                              div.className = 'battle-event-item animate-in';
                              if (evt.indexOf('damage') !== -1 || evt.indexOf('ATTACK') !== -1) div.classList.add('damage');
                              else if (evt.indexOf('Recovered') !== -1 || evt.indexOf('DEFENSE') !== -1) div.classList.add('gain');
                              else if (evt.indexOf('inflation') !== -1) div.classList.add('inflation');
                              div.textContent = evt;
                              eventsEl.appendChild(div);
                    }, 800 + i * 300);
          });

          // Check for critical hits (large deltas)
          var critEl = document.getElementById('battleCritical');
          var hasCritical = Math.abs(myData.arena_delta) > 50 || Math.abs(oppData.arena_delta) > 50;
          if (hasCritical) {
                    setTimeout(function() {
                              critEl.classList.remove('hidden');
                              critEl.classList.add('critical-animate');
                              playSound('critical');
                              // Screen shake
                              overlay.classList.add('screen-shake');
                              setTimeout(function() {
                                        overlay.classList.remove('screen-shake');
                              }, 500);
                    }, 600 + filteredEvents.length * 300 + 200);
          } else {
                    critEl.classList.add('hidden');
                    critEl.classList.remove('critical-animate');
          }

          // Show continue button after animations
          var continueBtn = document.getElementById('battleContinueBtn');
          continueBtn.style.opacity = '0';
          continueBtn.style.pointerEvents = 'none';
          var totalDelay = 1200 + filteredEvents.length * 300 + (hasCritical ? 800 : 0);
          setTimeout(function() {
                    continueBtn.style.opacity = '1';
                    continueBtn.style.pointerEvents = 'auto';
          }, totalDelay);
}

function closeBattleOverlay() {
          document.getElementById('battleOverlay').classList.add('hidden');
          document.getElementById('battleCritical').classList.add('hidden');
          document.getElementById('battleCritical').classList.remove('critical-animate');
          playSound('confirm');
}

/* ── Game Over Analytics ── */
function showAnalytics(data) {
          document.getElementById('analyticsOverlay').classList.remove('hidden');
          var banner = document.getElementById('winnerBanner');
          if (data.winner === myPlayerId) {
                    banner.textContent = '\uD83C\uDFC6 YOU WIN! \uD83C\uDFC6';
                    banner.style.color = 'var(--gold)';
                    playSound('victory');
          } else if (data.winner === 'draw') {
                    banner.textContent = "It's a Draw!";
                    banner.style.color = 'var(--muted)';
          } else {
                    banner.textContent = 'You Lost. Better luck next time!';
                    banner.style.color = 'var(--red)';
                    playSound('defeat');
          }
          var oppId = myPlayerId === 'player_1' ? 'player_2' : 'player_1';
          renderPlayerStats('p1Stats', data.analytics[myPlayerId]);
          document.getElementById('p1StatsTitle').textContent = 'You (Player ' + myPlayerNum + ')';
          renderPlayerStats('p2Stats', data.analytics[oppId]);
          document.getElementById('p2StatsTitle').textContent = 'Opponent';
          renderNWChart(data.analytics[myPlayerId].nw_history, data.analytics[oppId].nw_history);

          // Render LLM insights
          if (data.insights) {
                    renderInsights(data.insights, oppId);
          }

          // Request LLM-powered deep analysis
          requestLLMInsights();
}

function requestLLMInsights() {
          var section = document.getElementById('llmInsightsSection');
          var loading = document.getElementById('llmInsightsLoading');
          var content = document.getElementById('llmInsightsContent');
          var error = document.getElementById('llmInsightsError');

          section.style.display = '';
          loading.classList.remove('hidden');
          content.classList.add('hidden');
          error.classList.add('hidden');

          socket.emit('request_llm_insights', { player_id: myPlayerId });
}

function renderPlayerStats(id, a) {
          var p = a.total_profit;
          document.getElementById(id).innerHTML =
                    '<div class="stat-card"><div class="stat-label">Total Profit</div><div class="stat-value" style="color:' + (p >= 0 ? 'var(--green)' : 'var(--red)') + '">\u00A3' + p.toLocaleString('en-GB', { minimumFractionDigits: 2 }) + '</div></div>' +
                    '<div class="stat-card"><div class="stat-label">Options Win Rate</div><div class="stat-value" style="color:var(--accent)">' + a.options_win_rate + '%</div></div>' +
                    '<div class="stat-card"><div class="stat-label">Max Drawdown</div><div class="stat-value" style="color:var(--red)">-\u00A3' + a.max_drawdown.toLocaleString('en-GB', { minimumFractionDigits: 2 }) + '</div></div>' +
                    '<div class="stat-card"><div class="stat-label">Final NW</div><div class="stat-value" style="color:' + (a.final_nw >= 100000 ? 'var(--green)' : 'var(--gold)') + '">\u00A3' + a.final_nw.toLocaleString('en-GB', { minimumFractionDigits: 2 }) + '</div></div>';
}

function renderInsights(insights, oppId) {
          var myInsights = insights[myPlayerId] || [];
          var oppInsights = insights[oppId] || [];

          document.getElementById('insightsP1Title').textContent = 'Your Strategy Analysis';
          document.getElementById('insightsP2Title').textContent = 'Opponent Strategy Analysis';

          var p1List = document.getElementById('insightsP1');
          var p2List = document.getElementById('insightsP2');

          p1List.innerHTML = myInsights.map(function(insight) {
                    return '<li class="insight-item">' + insight + '</li>';
          }).join('');

          p2List.innerHTML = oppInsights.map(function(insight) {
                    return '<li class="insight-item">' + insight + '</li>';
          }).join('');
}

/* ── LLM Insights Rendering ── */
function handleLLMInsights(data) {
          var loading = document.getElementById('llmInsightsLoading');
          var content = document.getElementById('llmInsightsContent');
          var error = document.getElementById('llmInsightsError');

          loading.classList.add('hidden');

          if (data.content) {
                    content.innerHTML = renderMarkdown(data.content);
                    content.classList.remove('hidden');
          } else {
                    error.classList.remove('hidden');
          }
}

function renderMarkdown(md) {
          // Simple markdown to HTML converter for LLM output
          var html = md
                    // Escape HTML entities
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    // Headers
                    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
                    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
                    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
                    // Bold and italic
                    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*(.+?)\*/g, '<em>$1</em>')
                    // Unordered lists
                    .replace(/^[*\-] (.+)$/gm, '<li>$1</li>')
                    // Ordered lists
                    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
                    // Wrap consecutive <li> in <ul>
                    .replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>')
                    // Horizontal rules
                    .replace(/^---+$/gm, '<hr>')
                    // Line breaks for remaining lines
                    .replace(/\n\n/g, '</p><p>')
                    .replace(/\n/g, '<br>');

          return '<p>' + html + '</p>';
}
