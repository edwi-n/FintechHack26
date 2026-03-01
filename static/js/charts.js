/**
 * Trading Arena — Charts
 * =======================
 * Stock chart modal and analytics NW chart rendering.
 */

/* global Chart */

var stockChart = null;
var nwChart = null;

function requestStockChart(ticker, startIdx) {
          socket.emit('request_stock_chart', { ticker: ticker, start_idx: startIdx });
}

function showStockChart(data) {
          document.getElementById('chartModalTitle').textContent = data.ticker + ' — Last 6 Months (up to current date)';
          document.getElementById('chartModal').classList.remove('hidden');
          var ctx = document.getElementById('stockChartCanvas').getContext('2d');
          if (stockChart) stockChart.destroy();

          var lastIdx = data.prices.length - 1;
          var pointColors = data.prices.map(function (_, i) { return i === lastIdx ? '#f59e0b' : '#00d4ff'; });
          var pointRadii = data.prices.map(function (_, i) { return i === lastIdx ? 8 : 1; });

          // Show every ~8th date label to avoid clutter
          var sparseLabels = data.dates.map(function (d, i) { return i % 8 === 0 || i === lastIdx ? d : ''; });

          stockChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                              labels: sparseLabels,
                              datasets: [{
                                        label: data.ticker + ' Close Price',
                                        data: data.prices,
                                        borderColor: '#00d4ff',
                                        backgroundColor: 'rgba(0,212,255,0.08)',
                                        fill: true, tension: 0.2, borderWidth: 2,
                                        pointRadius: pointRadii,
                                        pointBackgroundColor: pointColors,
                              }],
                    },
                    options: {
                              responsive: true,
                              plugins: {
                                        title: { display: true, text: data.ticker + ' Historical Price (\u00A3)', color: '#e2e8f0', font: { size: 14 } },
                                        legend: { display: false },
                                        annotation: undefined,
                              },
                              scales: {
                                        y: { ticks: { color: '#94a3b8', callback: function (v) { return '\u00A3' + v.toFixed(0); } }, grid: { color: '#1e293b' } },
                                        x: { ticks: { color: '#94a3b8', maxRotation: 45 }, grid: { color: '#1e293b' } },
                              },
                    },
          });
}

function closeChartModal() {
          document.getElementById('chartModal').classList.add('hidden');
          if (stockChart) { stockChart.destroy(); stockChart = null; }
}

function renderNWChart(my) {
          var ctx = document.getElementById('nwChart').getContext('2d');
          var labels = my.map(function (_, i) { return i === 0 ? 'Start' : 'R' + i; });
          if (nwChart) nwChart.destroy();
          nwChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                              labels: labels,
                              datasets: [
                                        { label: 'Your Portfolio', data: my, borderColor: '#00d4ff', backgroundColor: 'rgba(0,212,255,0.1)', fill: true, tension: 0.3, borderWidth: 2, pointRadius: 4, pointBackgroundColor: '#00d4ff' },
                              ],
                    },
                    options: {
                              responsive: true,
                              plugins: {
                                        title: { display: true, text: 'Your Portfolio Value Over Time', color: '#e2e8f0', font: { size: 14 } },
                                        legend: { labels: { color: '#94a3b8' } },
                              },
                              scales: {
                                        y: { ticks: { color: '#94a3b8', callback: function (v) { return '\u00A3' + v.toLocaleString(); } }, grid: { color: '#1e293b' } },
                                        x: { ticks: { color: '#94a3b8' }, grid: { color: '#1e293b' } },
                              },
                    },
          });
}
