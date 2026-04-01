import logging
from flask import Flask, jsonify, render_template_string
from core import alpaca_trader, position_monitor, sheets_logger

logger = logging.getLogger(__name__)

app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>QuantBot Trading Executor</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: #0d1117;
      color: #c9d1d9;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      min-height: 100vh;
    }
    header {
      background: #161b22;
      border-bottom: 1px solid #30363d;
      padding: 16px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    header h1 { font-size: 18px; font-weight: 600; color: #f0f6fc; }
    header .status { font-size: 12px; color: #8b949e; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
    .badge-green { background: #1a3a2a; color: #3fb950; border: 1px solid #238636; }
    .badge-red { background: #3a1a1a; color: #f85149; border: 1px solid #da3633; }
    .badge-yellow { background: #3a2e00; color: #e3b341; border: 1px solid #9e6a03; }

    main { padding: 24px; max-width: 1400px; margin: 0 auto; }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .stat-card {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 20px;
    }
    .stat-card .label { font-size: 12px; color: #8b949e; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
    .stat-card .value { font-size: 28px; font-weight: 700; color: #f0f6fc; }
    .stat-card .value.green { color: #3fb950; }
    .stat-card .value.red { color: #f85149; }

    .section {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      margin-bottom: 24px;
      overflow: hidden;
    }
    .section-header {
      padding: 14px 20px;
      border-bottom: 1px solid #30363d;
      font-size: 14px;
      font-weight: 600;
      color: #f0f6fc;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .section-header .count {
      font-size: 11px;
      color: #8b949e;
      background: #21262d;
      padding: 2px 8px;
      border-radius: 10px;
    }

    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th { padding: 10px 16px; text-align: left; font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #30363d; }
    td { padding: 12px 16px; border-bottom: 1px solid #21262d; color: #c9d1d9; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #1c2128; }
    .no-data { text-align: center; color: #8b949e; padding: 40px; font-size: 13px; }

    .pnl-pos { color: #3fb950; }
    .pnl-neg { color: #f85149; }

    .chart-container { padding: 20px; height: 240px; }

    .refresh-bar {
      text-align: center;
      font-size: 11px;
      color: #8b949e;
      padding: 12px;
      border-top: 1px solid #30363d;
    }
    .dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #3fb950; margin-right: 6px; animation: pulse 2s infinite; }
    @keyframes pulse { 0%,100%{ opacity:1; } 50%{ opacity:0.3; } }
  </style>
</head>
<body>
  <header>
    <h1>⚡ QuantBot Trading Executor</h1>
    <div class="status">
      <span class="dot"></span>
      <span id="last-update">Loading...</span>
    </div>
  </header>

  <main>
    <div class="stats-grid" id="stats-grid">
      <div class="stat-card"><div class="label">Account Value</div><div class="value" id="stat-value">—</div></div>
      <div class="stat-card"><div class="label">Total Trades</div><div class="value" id="stat-total">—</div></div>
      <div class="stat-card"><div class="label">Wins</div><div class="value green" id="stat-wins">—</div></div>
      <div class="stat-card"><div class="label">Losses</div><div class="value red" id="stat-losses">—</div></div>
      <div class="stat-card"><div class="label">Win Rate</div><div class="value" id="stat-winrate">—</div></div>
      <div class="stat-card"><div class="label">Open Positions</div><div class="value" id="stat-open">—</div></div>
    </div>

    <div class="section">
      <div class="section-header">
        📈 Equity Curve
      </div>
      <div class="chart-container">
        <canvas id="equityChart"></canvas>
      </div>
    </div>

    <div class="section">
      <div class="section-header">
        Open Positions
        <span class="count" id="open-count">0</span>
      </div>
      <div id="positions-table">
        <div class="no-data">No open positions</div>
      </div>
    </div>

    <div class="section">
      <div class="section-header">
        Trade History
        <span class="count" id="history-count">0</span>
      </div>
      <div id="history-table">
        <div class="no-data">No trades yet</div>
      </div>
    </div>

    <div class="refresh-bar">Auto-refreshes every 30 seconds &nbsp;|&nbsp; <span id="next-refresh">30</span>s until next refresh</div>
  </main>

  <script>
    let equityChart = null;
    let countdown = 30;

    function fmt(n, dec=2) {
      if (n === null || n === undefined || n === '') return '—';
      return parseFloat(n).toFixed(dec);
    }
    function fmtUSD(n) {
      if (n === null || n === undefined) return '—';
      const v = parseFloat(n);
      return (v >= 0 ? '+' : '') + '$' + v.toFixed(2);
    }
    function pnlClass(n) {
      return parseFloat(n) >= 0 ? 'pnl-pos' : 'pnl-neg';
    }
    function badge(outcome) {
      if (!outcome) return '';
      const cls = outcome === 'WIN' ? 'badge-green' : outcome === 'LOSS' ? 'badge-red' : 'badge-yellow';
      return `<span class="badge ${cls}">${outcome}</span>`;
    }

    async function loadData() {
      try {
        const res = await fetch('/api/data');
        const d = await res.json();

        document.getElementById('stat-value').textContent = d.account_value ? '$' + parseFloat(d.account_value).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2}) : '—';
        document.getElementById('stat-total').textContent = d.total_trades ?? '—';
        document.getElementById('stat-wins').textContent = d.wins ?? '—';
        document.getElementById('stat-losses').textContent = d.losses ?? '—';
        document.getElementById('stat-winrate').textContent = d.win_rate ? d.win_rate + '%' : '—';
        document.getElementById('stat-open').textContent = d.open_positions?.length ?? 0;
        document.getElementById('last-update').textContent = 'Updated ' + new Date().toLocaleTimeString();

        renderPositions(d.open_positions || []);
        renderHistory(d.closed_trades || []);
        renderChart(d.equity_curve || []);
      } catch(e) {
        console.error('Failed to load data', e);
      }
    }

    function renderPositions(positions) {
      const el = document.getElementById('positions-table');
      document.getElementById('open-count').textContent = positions.length;
      if (!positions.length) { el.innerHTML = '<div class="no-data">No open positions</div>'; return; }
      let html = '<table><thead><tr><th>Symbol</th><th>Dir</th><th>Qty</th><th>Entry</th><th>Current</th><th>TP</th><th>SL</th><th>PnL%</th><th>PnL$</th><th>Hours Open</th><th>Confidence</th></tr></thead><tbody>';
      for (const p of positions) {
        const pc = pnlClass(p.pnl_pct);
        html += `<tr>
          <td><strong>${p.symbol}</strong></td>
          <td>${p.direction === 'BUY' ? '<span class="badge badge-green">BUY</span>' : '<span class="badge badge-red">SELL</span>'}</td>
          <td>${p.qty}</td>
          <td>$${fmt(p.entry)}</td>
          <td>$${fmt(p.current_price)}</td>
          <td>${p.take_profit ? '$'+fmt(p.take_profit) : '—'}</td>
          <td>${p.stop_loss ? '$'+fmt(p.stop_loss) : '—'}</td>
          <td class="${pc}">${p.pnl_pct >= 0 ? '+' : ''}${fmt(p.pnl_pct)}%</td>
          <td class="${pc}">${fmtUSD(p.pnl_dollar)}</td>
          <td>${p.hours_open}h</td>
          <td>${p.confidence ? p.confidence + '%' : '—'}</td>
        </tr>`;
      }
      html += '</tbody></table>';
      el.innerHTML = html;
    }

    function renderHistory(trades) {
      const el = document.getElementById('history-table');
      document.getElementById('history-count').textContent = trades.length;
      if (!trades.length) { el.innerHTML = '<div class="no-data">No closed trades yet</div>'; return; }
      let html = '<table><thead><tr><th>Date</th><th>Time</th><th>Symbol</th><th>Dir</th><th>Conf</th><th>Entry</th><th>Exit</th><th>Outcome</th><th>PnL%</th><th>PnL$</th><th>Duration</th></tr></thead><tbody>';
      const recent = [...trades].reverse().slice(0, 100);
      for (const t of recent) {
        const pc = pnlClass(t['PnL %'] || t.pnl_pct || 0);
        const pnlPct = t['PnL %'] ?? t.pnl_pct ?? 0;
        const pnlDollar = t['PnL $'] ?? t.pnl_dollar ?? 0;
        html += `<tr>
          <td>${t.Date || t.date || ''}</td>
          <td>${t.Time || t.time || ''}</td>
          <td><strong>${t.Symbol || t.symbol || ''}</strong></td>
          <td>${(t.Direction || t.direction || '') === 'BUY' ? '<span class="badge badge-green">BUY</span>' : '<span class="badge badge-red">SELL</span>'}</td>
          <td>${t.Confidence || t.confidence || '—'}</td>
          <td>$${fmt(t.Entry || t.entry)}</td>
          <td>$${fmt(t['Exit Price'] || t.exit_price)}</td>
          <td>${badge(t.Outcome || t.outcome)}</td>
          <td class="${pc}">${parseFloat(pnlPct) >= 0 ? '+' : ''}${fmt(pnlPct)}%</td>
          <td class="${pc}">${fmtUSD(pnlDollar)}</td>
          <td>${t.Duration || t.duration || '—'}</td>
        </tr>`;
      }
      html += '</tbody></table>';
      el.innerHTML = html;
    }

    function renderChart(equity) {
      const ctx = document.getElementById('equityChart').getContext('2d');
      const labels = equity.map((_, i) => `Trade ${i+1}`);
      const values = equity;
      if (equityChart) equityChart.destroy();
      equityChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels.length ? labels : ['Start'],
          datasets: [{
            label: 'Equity Curve',
            data: values.length ? values : [0],
            borderColor: '#3fb950',
            backgroundColor: 'rgba(63,185,80,0.08)',
            borderWidth: 2,
            fill: true,
            tension: 0.3,
            pointRadius: values.length <= 20 ? 4 : 0,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: '#8b949e', font: { size: 11 } }, grid: { color: '#21262d' } },
            y: { ticks: { color: '#8b949e', font: { size: 11 }, callback: v => '$' + v.toFixed(0) }, grid: { color: '#21262d' } },
          },
        },
      });
    }

    function tick() {
      countdown -= 1;
      document.getElementById('next-refresh').textContent = countdown;
      if (countdown <= 0) {
        countdown = 30;
        loadData();
      }
    }

    loadData();
    setInterval(tick, 1000);
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/data")
def api_data():
    try:
        account = alpaca_trader.get_account()
        account_value = float(account.portfolio_value) if account else None
    except Exception as e:
        logger.error(f"Failed to get account: {e}")
        account_value = None

    try:
        positions = position_monitor.get_position_summary()
    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        positions = []

    try:
        trades = sheets_logger.get_all_trades()
    except Exception as e:
        logger.error(f"Failed to get trades: {e}")
        trades = []

    wins = sum(1 for t in trades if (t.get("Outcome") or t.get("outcome", "")) == "WIN")
    losses = sum(1 for t in trades if (t.get("Outcome") or t.get("outcome", "")) == "LOSS")
    total = len(trades)
    win_rate = round(wins / total * 100, 1) if total else 0

    equity_curve = []
    running = float(account_value or 0)
    if account_value:
        equity_curve.append(running)
        for t in trades:
            pnl = t.get("PnL $") or t.get("pnl_dollar", 0)
            try:
                running += float(pnl)
                equity_curve.append(round(running, 2))
            except (ValueError, TypeError):
                pass

    return jsonify({
        "account_value": account_value,
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "open_positions": positions,
        "closed_trades": trades,
        "equity_curve": equity_curve,
    })


def run_dashboard():
    from config import settings
    logger.info(f"Starting dashboard on {settings.DASHBOARD_HOST}:{settings.DASHBOARD_PORT}")
    app.run(
        host=settings.DASHBOARD_HOST,
        port=settings.DASHBOARD_PORT,
        debug=False,
        use_reloader=False,
    )
