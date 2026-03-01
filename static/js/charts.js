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
          var pointColors = data.prices.map(function (_, i) { return i === lastIdx ? '#FFB800' : '#00FF41'; });
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
                                        borderColor: '#00FF41',
                                        backgroundColor: 'rgba(0,255,65,0.05)',
                                        fill: true, tension: 0.2, borderWidth: 2,
                                        pointRadius: pointRadii,
                                        pointBackgroundColor: pointColors,
                              }],
                    },
                    options: {
                              responsive: true,
                              plugins: {
                                        title: { display: true, text: data.ticker + ' Historical Price (\u00A3)', color: '#F0F0F0', font: { size: 14, family: 'monospace' } },
                                        legend: { display: false },
                                        annotation: undefined,
                              },
                              scales: {
                                        y: { ticks: { color: '#9A9A9A', font: { size: 12 }, callback: function (v) { return '\u00A3' + v.toFixed(0); } }, grid: { color: '#1A1A1A' } },
                                        x: { ticks: { color: '#9A9A9A', font: { size: 11 }, maxRotation: 45 }, grid: { color: '#1A1A1A' } },
                              },
                    },
          });
}

function closeChartModal() {
          document.getElementById('chartModal').classList.add('hidden');
          if (stockChart) { stockChart.destroy(); stockChart = null; }
}

function renderNWChart(my, opp) {
          var ctx = document.getElementById('nwChart').getContext('2d');
          var labels = my.map(function (_, i) { return i === 0 ? 'Start' : 'R' + i; });
          if (nwChart) nwChart.destroy();
          var datasets = [
                    { label: 'Your Portfolio', data: my, borderColor: '#00FF41', backgroundColor: 'rgba(0,255,65,0.05)', fill: true, tension: 0.3, borderWidth: 2, pointRadius: 4, pointBackgroundColor: '#00FF41' },
          ];
          if (opp) {
                    datasets.push({ label: 'Opponent', data: opp, borderColor: '#FF003C', backgroundColor: 'rgba(255,0,60,0.05)', fill: true, tension: 0.3, borderWidth: 2, pointRadius: 4, pointBackgroundColor: '#FF003C', borderDash: [6, 3] });
          }
          nwChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                              labels: labels,
                              datasets: datasets,
                    },
                    options: {
                              responsive: true,
                              plugins: {
                                        title: { display: true, text: 'Portfolio Value Over Time', color: '#F0F0F0', font: { size: 14, family: 'monospace' } },
                                        legend: { labels: { color: '#9A9A9A', font: { size: 12 } } },
                              },
                              scales: {
                                        y: { ticks: { color: '#9A9A9A', font: { size: 12 }, callback: function (v) { return '\u00A3' + v.toLocaleString(); } }, grid: { color: '#1A1A1A' } },
                                        x: { ticks: { color: '#9A9A9A', font: { size: 11 } }, grid: { color: '#1A1A1A' } },
                              },
                    },
          });
}
