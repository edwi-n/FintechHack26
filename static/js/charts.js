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
                                        title: { display: true, text: data.ticker + ' Historical Price (\u00A3)', color: '#C8C8C8', font: { size: 13, family: 'monospace' } },
                                        legend: { display: false },
                                        annotation: undefined,
                              },
                              scales: {
                                        y: { ticks: { color: '#555555', callback: function (v) { return '\u00A3' + v.toFixed(0); } }, grid: { color: '#1A1A1A' } },
                                        x: { ticks: { color: '#555555', maxRotation: 45 }, grid: { color: '#1A1A1A' } },
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
                                        { label: 'Your Portfolio', data: my, borderColor: '#00FF41', backgroundColor: 'rgba(0,255,65,0.05)', fill: true, tension: 0.3, borderWidth: 2, pointRadius: 4, pointBackgroundColor: '#00FF41' },
                              ],
                    },
                    options: {
                              responsive: true,
                              plugins: {
                                        title: { display: true, text: 'Your Portfolio Value Over Time', color: '#C8C8C8', font: { size: 13, family: 'monospace' } },
                                        legend: { labels: { color: '#555555' } },
                              },
                              scales: {
                                        y: { ticks: { color: '#555555', callback: function (v) { return '\u00A3' + v.toLocaleString(); } }, grid: { color: '#1A1A1A' } },
                                        x: { ticks: { color: '#555555' }, grid: { color: '#1A1A1A' } },
                              },
                    },
          });
}
