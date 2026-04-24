"""Cozy data dashboard for watching the simulation."""
from __future__ import annotations

from typing import Any, Optional

from flask import Flask, jsonify, render_template_string


app = Flask(__name__)
TOWN_DATA: dict[str, Any] = {"town": None, "runner": None}


def init_app(town_instance: Any = None, runner: Any = None) -> None:
    TOWN_DATA["town"] = town_instance
    TOWN_DATA["runner"] = runner


@app.get("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.get("/api/town")
def get_town_data():
    town = TOWN_DATA.get("town")
    if town is None:
        return jsonify({"error": "town is not initialized"}), 503
    return jsonify(town.get_town_overview())


@app.post("/api/start")
def start_town():
    runner = TOWN_DATA.get("runner")
    if runner:
        runner.start()
    return jsonify({"running": True})


@app.post("/api/stop")
def stop_town():
    runner = TOWN_DATA.get("runner")
    if runner:
        runner.stop()
    return jsonify({"running": False})


@app.post("/api/step")
def step_town():
    town = TOWN_DATA.get("town")
    if town is None:
        return jsonify({"error": "town is not initialized"}), 503
    return jsonify(town.simulate_tick())


@app.post("/api/reset")
def reset_town():
    runner = TOWN_DATA.get("runner")
    if runner:
        runner.reset()
    return jsonify({"reset": True})


@app.post("/api/speed/<int:speed>")
def set_speed(speed: int):
    runner = TOWN_DATA.get("runner")
    if runner:
        runner.set_speed(max(1, min(16, speed)))
    return jsonify({"speed": max(1, min(16, speed))})


def run_visualization_server(
    town_instance: Any,
    host: str = "127.0.0.1",
    port: int = 5000,
    debug: bool = False,
    runner: Optional[Any] = None,
) -> None:
    init_app(town_instance, runner)
    app.run(host=host, port=port, debug=debug, threaded=True)


HTML_TEMPLATE = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>UNASH-TOWN Data Dashboard</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4dfaa;
      --bg-soft: #ffe9b7;
      --panel: #fff7dc;
      --panel-2: #f8dda0;
      --wood: #7c4d2e;
      --wood-2: #b6753e;
      --line: #4c3024;
      --ink: #33251d;
      --muted: #73594b;
      --red: #bf4540;
      --green: #2f8954;
      --blue: #3f79a8;
      --amber: #cc8428;
      --shadow: rgba(76, 48, 36, 0.18);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: "Microsoft YaHei", "Trebuchet MS", Arial, sans-serif;
      background:
        linear-gradient(180deg, #98d4df 0 96px, transparent 96px),
        repeating-linear-gradient(45deg, rgba(255,255,255,0.14) 0 8px, transparent 8px 16px),
        var(--bg);
    }
    .shell {
      max-width: 1460px;
      margin: 0 auto;
      padding: 14px;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      margin-bottom: 12px;
      padding: 12px 14px;
      border: 4px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      box-shadow: 0 5px 0 var(--wood), 0 14px 26px var(--shadow);
    }
    h1 {
      margin: 0;
      font-size: 20px;
      line-height: 1.2;
      letter-spacing: 0;
    }
    .subtitle {
      margin-top: 3px;
      color: var(--muted);
      font-size: 12px;
    }
    .controls {
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 8px;
    }
    button {
      min-height: 34px;
      padding: 6px 12px;
      border: 3px solid var(--line);
      border-radius: 6px;
      background: var(--wood-2);
      color: #fff8d8;
      font-weight: 800;
      cursor: pointer;
      box-shadow: inset 0 -4px 0 rgba(67, 38, 25, 0.18), 0 3px 0 var(--line);
    }
    button:hover { transform: translateY(1px); box-shadow: inset 0 -3px 0 rgba(67, 38, 25, 0.18), 0 2px 0 var(--line); }
    button:active { transform: translateY(3px); box-shadow: inset 0 -2px 0 rgba(67, 38, 25, 0.18); }
    .grid {
      display: grid;
      grid-template-columns: minmax(560px, 1fr) minmax(420px, 0.72fr);
      gap: 12px;
    }
    .left, .right {
      display: grid;
      gap: 12px;
      align-content: start;
      min-width: 0;
    }
    .card {
      border: 4px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      box-shadow: 0 5px 0 var(--wood), 0 12px 24px var(--shadow);
      overflow: hidden;
      min-width: 0;
    }
    .card-title {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 10px 12px;
      border-bottom: 4px solid var(--line);
      background: #c98a4a;
      color: #fff8d8;
      font-weight: 800;
    }
    .card-body { padding: 12px; }
    .metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 9px;
    }
    .metric {
      min-height: 76px;
      border: 3px solid #6b4432;
      border-radius: 6px;
      background: var(--bg-soft);
      padding: 9px;
      box-shadow: inset 0 -4px 0 rgba(120, 74, 43, 0.10);
    }
    .label {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.25;
    }
    .value {
      margin-top: 6px;
      font-size: 20px;
      line-height: 1.15;
      font-weight: 900;
      overflow-wrap: anywhere;
    }
    .chart-wrap {
      height: 260px;
      border: 3px solid #6b4432;
      border-radius: 6px;
      background:
        linear-gradient(rgba(255,255,255,0.35), rgba(255,255,255,0.10)),
        #ffefc0;
      padding: 8px;
    }
    canvas {
      width: 100%;
      height: 100%;
      display: block;
      image-rendering: pixelated;
    }
    table {
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      overflow: hidden;
      border: 3px solid #6b4432;
      border-radius: 6px;
      background: #fff8df;
      table-layout: fixed;
    }
    th, td {
      padding: 8px 9px;
      border-bottom: 2px solid #e0bd80;
      text-align: left;
      font-size: 12px;
      line-height: 1.35;
      vertical-align: middle;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    th {
      background: #e9bd75;
      color: #3b281f;
      font-weight: 900;
    }
    tr:last-child td { border-bottom: 0; }
    tbody tr:nth-child(even) td { background: #fff1c8; }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .up { color: var(--red); }
    .down { color: var(--green); }
    .tag {
      display: inline-block;
      max-width: 100%;
      padding: 2px 6px;
      border: 2px solid #6b4432;
      border-radius: 5px;
      background: #f2d28b;
      color: #5c371f;
      font-weight: 800;
      overflow: hidden;
      text-overflow: ellipsis;
      vertical-align: middle;
    }
    .two-col {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    @media (max-width: 1080px) {
      .grid { grid-template-columns: 1fr; }
      .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 640px) {
      .shell { padding: 10px; }
      header { align-items: flex-start; flex-direction: column; }
      .controls { justify-content: flex-start; }
      .metrics, .two-col { grid-template-columns: 1fr; }
      th, td { padding: 7px; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>UNASH-TOWN 温暖数据看板</h1>
        <div class="subtitle">保留研究数据密度，只给表格、行情和记录换一层轻松的像素小镇皮肤。</div>
      </div>
      <div class="controls">
        <button onclick="start()" title="开始自动推进">开始</button>
        <button onclick="stop()" title="暂停自动推进">暂停</button>
        <button onclick="step()" title="推进一分钟">单步</button>
        <button onclick="speed()" title="切换模拟速度">速度 <span id="speed">1x</span></button>
      </div>
    </header>

    <div class="grid">
      <section class="left">
        <section class="card">
          <div class="card-title">
            <span>行情概览</span>
            <span id="clock">第 1 天 09:30</span>
          </div>
          <div class="card-body">
            <div class="metrics" id="metrics"></div>
          </div>
        </section>

        <section class="card">
          <div class="card-title">
            <span>价格曲线</span>
            <span id="phase">准备开市</span>
          </div>
          <div class="card-body">
            <div class="chart-wrap"><canvas id="priceChart"></canvas></div>
          </div>
        </section>

        <section class="card">
          <div class="card-title">
            <span>交易者状态表</span>
            <span id="agent-count">0 人</span>
          </div>
          <div class="card-body">
            <table>
              <thead>
                <tr>
                  <th style="width: 15%">排名</th>
                  <th style="width: 21%">姓名</th>
                  <th style="width: 17%">类型</th>
                  <th style="width: 17%">风格</th>
                  <th class="num" style="width: 15%">总资产</th>
                  <th class="num" style="width: 15%">收益率</th>
                </tr>
              </thead>
              <tbody id="agents"></tbody>
            </table>
          </div>
        </section>
      </section>

      <section class="right">
        <section class="card">
          <div class="card-title">
            <span>市场细节</span>
            <span id="security-code">SIM001</span>
          </div>
          <div class="card-body">
            <table>
              <tbody id="market-detail"></tbody>
            </table>
          </div>
        </section>

        <section class="card">
          <div class="card-title">
            <span>最近成交</span>
            <span id="trade-count">0 笔</span>
          </div>
          <div class="card-body">
            <table>
              <thead>
                <tr>
                  <th style="width: 26%">价格</th>
                  <th style="width: 24%">数量</th>
                  <th style="width: 25%">买方</th>
                  <th style="width: 25%">卖方</th>
                </tr>
              </thead>
              <tbody id="trades"></tbody>
            </table>
          </div>
        </section>

        <section class="card">
          <div class="card-title">
            <span>风格分布</span>
            <span>实时</span>
          </div>
          <div class="card-body">
            <table>
              <thead>
                <tr>
                  <th>风格</th>
                  <th class="num">人数</th>
                </tr>
              </thead>
              <tbody id="styles"></tbody>
            </table>
          </div>
        </section>
      </section>
    </div>
  </div>

  <script>
    const chart = document.getElementById("priceChart");
    const ctx = chart.getContext("2d");
    let data = null;
    let speedValue = 1;
    let priceHistory = [];

    const phaseNames = {
      opening_call: "集合竞价",
      morning_continuous: "上午连续竞价",
      lunch_break: "午间休市",
      afternoon_continuous: "下午连续竞价",
      closing_call: "尾盘集合竞价",
      closed: "休市"
    };

    function cls(value) {
      return Number(value) >= 0 ? "up" : "down";
    }

    function fmt(value, digits = 2) {
      return Number(value || 0).toLocaleString("zh-CN", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits
      });
    }

    async function fetchData() {
      const res = await fetch("/api/town");
      data = await res.json();
      if (!data || data.error) return;
      const price = Number(data.market.price);
      const last = priceHistory[priceHistory.length - 1];
      if (!last || last.day !== data.day || last.time !== data.time || last.price !== price) {
        priceHistory.push({ day: data.day, time: data.time, price });
        if (priceHistory.length > 180) priceHistory.shift();
      }
      render();
      drawChart();
    }

    async function start() { await fetch("/api/start", {method: "POST"}); }
    async function stop() { await fetch("/api/stop", {method: "POST"}); }
    async function step() { await fetch("/api/step", {method: "POST"}); await fetchData(); }
    async function speed() {
      speedValue = speedValue >= 8 ? 1 : speedValue * 2;
      document.getElementById("speed").textContent = speedValue + "x";
      await fetch("/api/speed/" + speedValue, {method: "POST"});
    }

    function render() {
      const m = data.market;
      const phase = phaseNames[data.phase] || data.phase;
      document.getElementById("clock").textContent = `第 ${data.day} 天 ${data.time}`;
      document.getElementById("phase").textContent = phase;
      document.getElementById("security-code").textContent = m.code || "SIM001";

      document.getElementById("metrics").innerHTML = `
        <div class="metric"><div class="label">当前价格</div><div class="value ${cls(m.change_pct)}">${fmt(m.price)}</div></div>
        <div class="metric"><div class="label">今日涨跌</div><div class="value ${cls(m.change_pct)}">${fmt(m.change_pct)}%</div></div>
        <div class="metric"><div class="label">成交量</div><div class="value">${Number(m.volume || 0).toLocaleString("zh-CN")}</div></div>
        <div class="metric"><div class="label">成交笔数</div><div class="value">${data.stats.total_trades}</div></div>
      `;

      const details = [
        ["证券名称", m.name],
        ["昨收", fmt(m.previous_close)],
        ["开盘", fmt(m.day_open)],
        ["最高", fmt(m.day_high)],
        ["最低", fmt(m.day_low)],
        ["涨停", fmt(m.limit_up)],
        ["跌停", fmt(m.limit_down)],
        ["市场状态", m.regime],
        ["事件", m.event],
        ["波动率", fmt(m.volatility, 4)]
      ];
      document.getElementById("market-detail").innerHTML = details.map(([k, v]) => `
        <tr><th>${k}</th><td class="num">${v}</td></tr>
      `).join("");

      const agents = [...data.agents].sort((a, b) => b.total_value - a.total_value);
      document.getElementById("agent-count").textContent = `${agents.length} 人`;
      document.getElementById("agents").innerHTML = agents.map((a, i) => `
        <tr>
          <td>${i + 1}</td>
          <td title="${a.name}">${a.name}</td>
          <td><span class="tag">${a.label}</span></td>
          <td title="${a.dominant_style}">${a.dominant_style}</td>
          <td class="num">${fmt(a.total_value, 0)}</td>
          <td class="num ${cls(a.return_rate)}">${fmt(a.return_rate)}%</td>
        </tr>
      `).join("");

      const trades = (data.recent_trades || []).slice(-8).reverse();
      document.getElementById("trade-count").textContent = `${trades.length} 笔`;
      document.getElementById("trades").innerHTML = trades.length ? trades.map((t) => `
        <tr>
          <td class="num">${fmt(t.price)}</td>
          <td class="num">${Number(t.quantity || 0).toLocaleString("zh-CN")}</td>
          <td title="${t.buyer}">${t.buyer}</td>
          <td title="${t.seller}">${t.seller}</td>
        </tr>
      `).join("") : `<tr><td colspan="4">暂无成交</td></tr>`;

      const styles = {};
      data.agents.forEach((agent) => {
        styles[agent.dominant_style] = (styles[agent.dominant_style] || 0) + 1;
      });
      document.getElementById("styles").innerHTML = Object.entries(styles)
        .sort((a, b) => b[1] - a[1])
        .map(([style, count]) => `<tr><td>${style}</td><td class="num">${count}</td></tr>`)
        .join("");
    }

    function resizeChart() {
      const rect = chart.getBoundingClientRect();
      chart.width = Math.max(1, Math.floor(rect.width * devicePixelRatio));
      chart.height = Math.max(1, Math.floor(rect.height * devicePixelRatio));
      ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
      drawChart();
    }

    function drawChart() {
      const w = chart.clientWidth;
      const h = chart.clientHeight;
      if (!w || !h) return;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "#ffefc0";
      ctx.fillRect(0, 0, w, h);

      ctx.strokeStyle = "#e0bd80";
      ctx.lineWidth = 1;
      for (let i = 1; i < 6; i++) {
        const y = (h / 6) * i;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }
      for (let i = 1; i < 8; i++) {
        const x = (w / 8) * i;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      }

      if (priceHistory.length < 2) {
        ctx.fillStyle = "#73594b";
        ctx.font = "13px sans-serif";
        ctx.fillText("等待价格数据...", 14, 24);
        return;
      }

      const prices = priceHistory.map((item) => item.price);
      const min = Math.min(...prices);
      const max = Math.max(...prices);
      const span = Math.max(0.01, max - min);
      const pad = 20;
      const xOf = (index) => pad + (index / Math.max(1, priceHistory.length - 1)) * (w - pad * 2);
      const yOf = (price) => h - pad - ((price - min) / span) * (h - pad * 2);

      ctx.strokeStyle = "#4c3024";
      ctx.lineWidth = 4;
      ctx.beginPath();
      priceHistory.forEach((point, index) => {
        const x = xOf(index);
        const y = yOf(point.price);
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();

      ctx.strokeStyle = data && data.market.change_pct >= 0 ? "#bf4540" : "#2f8954";
      ctx.lineWidth = 2;
      ctx.beginPath();
      priceHistory.forEach((point, index) => {
        const x = xOf(index);
        const y = yOf(point.price);
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();

      ctx.fillStyle = "#33251d";
      ctx.font = "12px sans-serif";
      ctx.fillText(`高 ${fmt(max)}`, 12, 18);
      ctx.fillText(`低 ${fmt(min)}`, 12, h - 10);
    }

    addEventListener("resize", resizeChart);
    resizeChart();
    fetchData();
    setInterval(fetchData, 900);
  </script>
</body>
</html>
"""
