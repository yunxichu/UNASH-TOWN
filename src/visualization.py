"""Small Flask dashboard for watching the simulation."""
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
  <title>UNASH-TOWN Dashboard</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #101418;
      --panel: #171d23;
      --line: #28323c;
      --text: #edf2f7;
      --muted: #9aa7b2;
      --red: #f15b5b;
      --green: #55c486;
      --blue: #6aa8ff;
      --amber: #e8b86d;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, "Microsoft YaHei", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 14px 20px;
      border-bottom: 1px solid var(--line);
      background: #12181e;
    }
    h1 { margin: 0; font-size: 18px; font-weight: 700; }
    button {
      border: 1px solid var(--line);
      background: #202833;
      color: var(--text);
      padding: 8px 12px;
      border-radius: 6px;
      cursor: pointer;
    }
    button:hover { border-color: var(--blue); }
    main {
      display: grid;
      grid-template-columns: minmax(420px, 1.2fr) minmax(380px, 0.8fr);
      min-height: calc(100vh - 58px);
    }
    .stage {
      position: relative;
      padding: 20px;
      border-right: 1px solid var(--line);
    }
    canvas {
      width: 100%;
      height: calc(100vh - 98px);
      display: block;
      background: #0d1217;
      border: 1px solid var(--line);
      border-radius: 8px;
    }
    aside { padding: 20px; overflow: auto; max-height: calc(100vh - 58px); }
    .metrics {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 18px;
    }
    .metric, .agent {
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
      padding: 12px;
    }
    .label { color: var(--muted); font-size: 12px; }
    .value { font-size: 22px; font-weight: 700; margin-top: 4px; }
    .agents { display: grid; gap: 8px; }
    .agent { display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: center; }
    .agent strong { font-size: 14px; }
    .tag { color: var(--amber); font-size: 12px; }
    .sub { color: var(--muted); font-size: 12px; }
    .up { color: var(--red); }
    .down { color: var(--green); }
    @media (max-width: 900px) {
      main { grid-template-columns: 1fr; }
      .stage { border-right: none; border-bottom: 1px solid var(--line); }
      canvas { height: 55vh; }
    }
  </style>
</head>
<body>
  <header>
    <h1>UNASH-TOWN · 异质交易者小镇</h1>
    <div>
      <button onclick="start()">Start</button>
      <button onclick="stop()">Stop</button>
      <button onclick="step()">Step</button>
      <button onclick="speed()">Speed <span id="speed">1x</span></button>
    </div>
  </header>
  <main>
    <section class="stage"><canvas id="town"></canvas></section>
    <aside>
      <div class="metrics" id="metrics"></div>
      <div class="agents" id="agents"></div>
    </aside>
  </main>
  <script>
    const canvas = document.getElementById("town");
    const ctx = canvas.getContext("2d");
    let data = null;
    let speedValue = 1;

    function resize() {
      const rect = canvas.getBoundingClientRect();
      canvas.width = Math.floor(rect.width * devicePixelRatio);
      canvas.height = Math.floor(rect.height * devicePixelRatio);
      ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
      draw();
    }
    addEventListener("resize", resize);

    async function fetchData() {
      const res = await fetch("/api/town");
      data = await res.json();
      render();
      draw();
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
      if (!data || data.error) return;
      const m = data.market;
      const cls = m.change_pct >= 0 ? "up" : "down";
      document.getElementById("metrics").innerHTML = `
        <div class="metric"><div class="label">时间</div><div class="value">${data.day} / ${data.time}</div></div>
        <div class="metric"><div class="label">阶段</div><div class="value">${data.phase}</div></div>
        <div class="metric"><div class="label">价格</div><div class="value ${cls}">${m.price.toFixed(2)}</div></div>
        <div class="metric"><div class="label">涨跌</div><div class="value ${cls}">${m.change_pct.toFixed(2)}%</div></div>
        <div class="metric"><div class="label">Regime</div><div class="value">${m.regime}</div></div>
        <div class="metric"><div class="label">成交</div><div class="value">${data.stats.total_trades}</div></div>
      `;
      const agents = [...data.agents].sort((a, b) => b.total_value - a.total_value);
      document.getElementById("agents").innerHTML = agents.map((a, i) => `
        <div class="agent">
          <div>
            <strong>${i + 1}. ${a.name}</strong> <span class="tag">${a.label}</span>
            <div class="sub">style=${a.dominant_style} · pos=${a.position} · win=${a.win_rate}%</div>
          </div>
          <div class="${a.return_rate >= 0 ? "up" : "down"}">${a.return_rate.toFixed(2)}%</div>
        </div>
      `).join("");
    }

    function draw() {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "#0d1217";
      ctx.fillRect(0, 0, w, h);
      ctx.strokeStyle = "#28323c";
      ctx.lineWidth = 2;
      for (let i = 1; i < 5; i++) {
        ctx.beginPath(); ctx.moveTo((w / 5) * i, 20); ctx.lineTo((w / 5) * i, h - 20); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(20, (h / 5) * i); ctx.lineTo(w - 20, (h / 5) * i); ctx.stroke();
      }
      ctx.fillStyle = "#e8b86d";
      ctx.fillRect(w * 0.43, h * 0.40, w * 0.14, h * 0.18);
      ctx.fillStyle = "#edf2f7";
      ctx.font = "13px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Exchange", w * 0.50, h * 0.50);
      if (!data || !data.agents) return;
      data.agents.forEach((agent, index) => {
        const angle = (Math.PI * 2 * index) / data.agents.length;
        const radius = Math.min(w, h) * (0.26 + (index % 3) * 0.035);
        const x = w / 2 + Math.cos(angle) * radius;
        const y = h / 2 + Math.sin(angle) * radius;
        ctx.beginPath();
        ctx.arc(x, y, 9 + Math.min(8, Math.abs(agent.return_rate) / 4), 0, Math.PI * 2);
        ctx.fillStyle = agent.return_rate >= 0 ? "#f15b5b" : "#55c486";
        ctx.fill();
        ctx.fillStyle = "#edf2f7";
        ctx.font = "11px sans-serif";
        ctx.fillText(agent.name.split("-")[0], x, y - 14);
      });
    }

    resize();
    fetchData();
    setInterval(fetchData, 900);
  </script>
</body>
</html>
"""
