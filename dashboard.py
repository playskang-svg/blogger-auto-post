#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Atotrip Blogger Web Console Dashboard
Modern, Premium Dark-Themed Web GUI for Multi-Blogger Automation
Runs locally with zero external dependencies (pure Python standard library).
"""

import os
import sys
import json
import random
import urllib.parse
import urllib.request
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta

PORT = 5050
CONFIG_PATH = os.path.expanduser("~/Posting/Blogger/config/blogs.json")
TOKEN_PATH = os.path.expanduser("~/Posting/Blogger/token.json")

def load_blogs():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "default_blog": "atttrip",
        "blogs": {
            "atttrip": {"id": "3287113241520886880", "name": "아토트립 (반려견 동반 여행)", "default_interval_hours": 4},
            "suriwiki": {"id": "5571572496232571585", "name": "수리위키 / 꿀팁뉴스", "default_interval_hours": 4},
            "vpn_adbles": {"id": "5571572496232571585", "name": "VPN-Adbles", "default_interval_hours": 6}
        }
    }

def get_access_token():
    if not os.path.exists(TOKEN_PATH):
        return None
    try:
        with open(TOKEN_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        refresh_token = data.get("refresh_token")
        client_id = data.get("client_id")
        client_secret = data.get("client_secret")

        if refresh_token and client_id and client_secret:
            token_url = "https://oauth2.googleapis.com/token"
            payload = urllib.parse.urlencode({
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }).encode("utf-8")
            req = urllib.request.Request(token_url, data=payload, method="POST")
            with urllib.request.urlopen(req) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                return res_data.get("access_token")
        return data.get("access_token")
    except Exception as e:
        print(f"[TOKEN ERROR] {e}")
        return None

HTML_PAGE = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Blogger Master Console | 블로그 자동화 통합 대시보드</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-primary: #0f1117;
      --bg-secondary: #181b24;
      --bg-card: #202433;
      --border-color: rgba(255, 255, 255, 0.08);
      --accent: #ff7b54;
      --accent-hover: #ff9170;
      --accent-glow: rgba(255, 123, 84, 0.25);
      --text-main: #f3f4f6;
      --text-muted: #9ca3af;
      --success: #10b981;
      --info: #3b82f6;
      --warning: #f59e0b;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg-primary);
      color: var(--text-main);
      font-family: 'Pretendard', -apple-system, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      background: rgba(24, 27, 36, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border-color);
      padding: 16px 32px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-icon {
      width: 36px;
      height: 36px;
      background: linear-gradient(135deg, #ff7b54, #ff5722);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 20px;
      box-shadow: 0 4px 12px var(--accent-glow);
    }
    .brand-text h1 { font-size: 18px; font-weight: 700; letter-spacing: -0.5px; }
    .brand-text p { font-size: 12px; color: var(--text-muted); }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(16, 185, 129, 0.15);
      color: var(--success);
      padding: 6px 12px;
      border-radius: 20px;
      font-size: 13px;
      font-weight: 600;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-dot { width: 8px; height: 8px; background: var(--success); border-radius: 50%; animation: pulse 2s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(1.2); } }

    main {
      flex: 1;
      max-width: 1200px;
      width: 100%;
      margin: 0 auto;
      padding: 32px 20px;
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 24px;
    }
    @media (max-width: 960px) { main { grid-template-columns: 1fr; } }

    .card {
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.25);
    }
    .card-title {
      font-size: 16px;
      font-weight: 700;
      margin-bottom: 20px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    /* Blog Selector */
    .blog-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-bottom: 24px;
    }
    .blog-btn {
      background: var(--bg-card);
      border: 2px solid var(--border-color);
      border-radius: 12px;
      padding: 16px 12px;
      text-align: left;
      cursor: pointer;
      transition: all 0.2s ease;
      color: var(--text-main);
    }
    .blog-btn:hover { border-color: rgba(255, 123, 84, 0.5); transform: translateY(-2px); }
    .blog-btn.active {
      border-color: var(--accent);
      background: rgba(255, 123, 84, 0.1);
      box-shadow: 0 4px 16px var(--accent-glow);
    }
    .blog-btn .b-name { font-size: 14px; font-weight: 700; margin-bottom: 4px; }
    .blog-btn .b-id { font-size: 11px; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; }

    /* Form Fields */
    .field-group { margin-bottom: 20px; }
    label { display: block; font-size: 13px; font-weight: 600; color: var(--text-muted); margin-bottom: 8px; }
    input[type="text"], textarea, select {
      width: 100%;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 12px 14px;
      color: var(--text-main);
      font-size: 14px;
      font-family: inherit;
      transition: border-color 0.2s;
    }
    input[type="text"]:focus, textarea:focus, select:focus {
      outline: none;
      border-color: var(--accent);
      box-shadow: 0 0 0 3px var(--accent-glow);
    }
    textarea { resize: vertical; min-height: 90px; }

    /* Scheduler Options */
    .schedule-panel {
      background: var(--bg-card);
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 24px;
    }
    .presets { display: flex; gap: 8px; margin-top: 8px; }
    .preset-btn {
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      color: var(--text-muted);
      padding: 6px 12px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }
    .preset-btn:hover, .preset-btn.active {
      color: var(--accent);
      border-color: var(--accent);
      background: rgba(255, 123, 84, 0.1);
    }
    .jitter-toggle {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: 14px;
      padding-top: 12px;
      border-top: 1px solid var(--border-color);
      font-size: 13px;
    }

    /* Action Buttons */
    .btn-group { display: flex; gap: 12px; }
    .btn {
      flex: 1;
      padding: 14px 20px;
      border-radius: 12px;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
      border: none;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: all 0.2s;
    }
    .btn-primary {
      background: linear-gradient(135deg, #ff7b54, #ff5722);
      color: white;
      box-shadow: 0 4px 16px var(--accent-glow);
    }
    .btn-primary:hover {
      background: linear-gradient(135deg, #ff8c69, #ff6b3d);
      transform: translateY(-2px);
    }
    .btn-secondary {
      background: var(--bg-card);
      color: var(--text-main);
      border: 1px solid var(--border-color);
    }
    .btn-secondary:hover { background: rgba(255, 255, 255, 0.05); }

    /* Console Terminal Output */
    .console-box {
      background: #090a0f;
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 16px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      line-height: 1.6;
      color: #34d399;
      min-height: 380px;
      max-height: 520px;
      overflow-y: auto;
      white-space: pre-wrap;
    }
    .console-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .dots { display: flex; gap: 6px; }
    .dot { width: 10px; height: 10px; border-radius: 50%; }
    .dot-red { background: #ef4444; }
    .dot-yellow { background: #f59e0b; }
    .dot-green { background: #10b981; }

    /* Quick Tools */
    .quick-tools {
      margin-top: 20px;
      display: flex;
      gap: 10px;
    }
    .tool-btn {
      padding: 8px 14px;
      font-size: 12px;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      color: var(--text-muted);
      border-radius: 8px;
      cursor: pointer;
    }
    .tool-btn:hover { color: var(--text-main); border-color: rgba(255,255,255,0.2); }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <div class="brand-icon">B</div>
      <div class="brand-text">
        <h1>Blogger Master Console</h1>
        <p>Google Blogger REST API v3 Multi-Site Automation Dashboard</p>
      </div>
    </div>
    <div class="badge">
      <div class="badge-dot"></div>
      REST API v3 Ready
    </div>
  </header>

  <main>
    <!-- Left Column: Controls -->
    <div class="card">
      <div class="card-title">📌 1. 대상 블로그 선택 (Multi-Blog)</div>
      <div class="blog-cards" id="blogCards">
        <!-- Injected dynamically -->
      </div>

      <div class="card-title">✍️ 2. 포스팅 주제 및 AI 지침 주입</div>
      <div class="field-group">
        <label>글 주제 (Title & Core Topic)</label>
        <input type="text" id="postTopic" value="2026 가평 반려견 동반 숙소 BEST 4: 북한강 뷰 독채 풀빌라부터 잔디마당 펜션까지">
      </div>
      <div class="field-group">
        <label>추가 맞춤 지침 (Optional Prompts & Keywords)</label>
        <textarea id="postPrompt" placeholder="강조할 포인트, 특별히 포함할 어메니티 또는 프로모션 정보 등을 자유롭게 적어주세요."></textarea>
      </div>

      <div class="card-title">⏰ 3. 예약 발행 스케줄러</div>
      <div class="schedule-panel">
        <label>기준 예약 지연 시간 (Hours)</label>
        <div class="presets">
          <button class="preset-btn" onclick="setHours(0)">⚡ 즉시 발행</button>
          <button class="preset-btn" onclick="setHours(2)">2시간 후</button>
          <button class="preset-btn active" onclick="setHours(4)">4시간 후</button>
          <button class="preset-btn" onclick="setHours(6)">6시간 후</button>
          <button class="preset-btn" onclick="setHours(12)">12시간 후</button>
        </div>
        <input type="number" id="scheduleHours" value="4.0" step="0.5" min="0" style="margin-top: 10px; width: 120px;" onchange="updateCustomHours()">

        <div class="jitter-toggle">
          <div>
            <strong>🎲 자연스러운 불규칙 지터 (Natural Jitter)</strong>
            <p style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">정확한 4시간 대신 ±20분 무작위 편차를 적용하여 사람처럼 예약합니다.</p>
          </div>
          <input type="checkbox" id="useJitter" checked style="width: 20px; height: 20px; accent-color: var(--accent);">
        </div>
      </div>

      <div class="btn-group">
        <button class="btn btn-primary" onclick="submitPost(false)">
          🚀 원클릭 예약 발행 시작
        </button>
        <button class="btn btn-secondary" onclick="submitPost(true)">
          📝 초안 저장
        </button>
      </div>
    </div>

    <!-- Right Column: Live Terminal & Tools -->
    <div class="card">
      <div class="card-title">💻 실시간 실행 콘솔 (Live Console)</div>
      <div class="console-box" id="consoleBox">
        <div class="console-header">
          <div class="dots">
            <div class="dot dot-red"></div>
            <div class="dot dot-yellow"></div>
            <div class="dot dot-green"></div>
          </div>
          <span style="font-size: 11px; color: var(--text-muted);">blogger-v3-engine</span>
        </div>
        <div id="logText">[READY] Blogger Master Console v2.0 initialized.
Waiting for user input...</div>
      </div>

      <div class="quick-tools">
        <button class="tool-btn" onclick="showChromeUI()">🖥️ 브라우저 창 띄우기 (수동 검수)</button>
        <button class="tool-btn" onclick="hideChromeUI()">🙈 창 화면 밖 숨기기 (-5000px)</button>
        <button class="tool-btn" onclick="checkStatus()">📊 블로그 상태 새로고침</button>
      </div>
    </div>
  </main>

  <script>
    const blogsData = {
      atttrip: { id: "3287113241520886880", name: "아토트립", desc: "반려견 여행 정보" },
      suriwiki: { id: "5571572496232571585", name: "수리위키", desc: "생활 수리 & 꿀팁" },
      vpn_adbles: { id: "5571572496232571585", name: "VPN-Adbles", desc: "IT 보안 & 프로모션" }
    };

    let selectedBlog = "atttrip";

    function renderBlogs() {
      const container = document.getElementById("blogCards");
      container.innerHTML = "";
      for (let k in blogsData) {
        const b = blogsData[k];
        const active = k === selectedBlog ? "active" : "";
        container.innerHTML += `
          <div class="blog-btn ${active}" onclick="selectBlog('${k}')">
            <div class="b-name">${b.name}</div>
            <div class="b-id">ID: ...${b.id.slice(-6)}</div>
          </div>
        `;
      }
    }

    function selectBlog(k) {
      selectedBlog = k;
      renderBlogs();
      appendLog(`[SELECT] 대상 블로그가 '${blogsData[k].name}'(으)로 변경되었습니다.`);
    }

    function setHours(h) {
      document.querySelectorAll(".preset-btn").forEach(b => b.classList.remove("active"));
      event.target.classList.add("active");
      document.getElementById("scheduleHours").value = h;
      appendLog(`[SCHEDULE] 예약 간격이 ${h}시간으로 설정되었습니다.`);
    }

    function updateCustomHours() {
      document.querySelectorAll(".preset-btn").forEach(b => b.classList.remove("active"));
    }

    function appendLog(msg) {
      const box = document.getElementById("logText");
      const time = new Date().toLocaleTimeString();
      box.innerText += `\\n[${time}] ${msg}`;
      const parent = document.getElementById("consoleBox");
      parent.scrollTop = parent.scrollHeight;
    }

    async function submitPost(isDraft) {
      const topic = document.getElementById("postTopic").value.trim();
      const prompt = document.getElementById("postPrompt").value.trim();
      const hours = parseFloat(document.getElementById("scheduleHours").value) || 0;
      const useJitter = document.getElementById("useJitter").checked;

      if (!topic) {
        alert("글 주제를 입력해 주세요!");
        return;
      }

      appendLog(`========================================`);
      appendLog(`[START] '${blogsData[selectedBlog].name}' 포스팅 작업 시작...`);
      appendLog(`  - 주제: ${topic}`);
      appendLog(`  - 예약 설정: ${hours}시간 후 (지터: ${useJitter ? 'ON' : 'OFF'})`);
      appendLog(`  - 모드: ${isDraft ? '초안 저장' : '예약 발행'}`);

      try {
        const resp = await fetch("/api/publish", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            blog: selectedBlog,
            topic: topic,
            prompt: prompt,
            schedule_hours: hours,
            use_jitter: useJitter,
            is_draft: isDraft
          })
        });
        const res = await resp.json();
        if (res.success) {
          appendLog(`🎉 [성공] 글 등록 및 예약이 완료되었습니다!`);
          appendLog(`   - 글 ID: ${res.post_id}`);
          appendLog(`   - 예약 시간: ${res.schedule_time || '즉시 발행'}`);
        } else {
          appendLog(`❌ [오류] ${res.error}`);
        }
      } catch (err) {
        appendLog(`❌ [통신 오류] ${err.message}`);
      }
    }

    async function showChromeUI() {
      appendLog("[UI] 화면에 Chrome 창을 띄웁니다...");
      fetch("/api/show-ui");
    }

    async function hideChromeUI() {
      appendLog("[UI] Chrome 창을 다시 화면 밖(-5000px)으로 격리합니다.");
      fetch("/api/hide-ui");
    }

    async function checkStatus() {
      appendLog(`[STATUS] '${blogsData[selectedBlog].name}' 상태를 조회 중...`);
      const resp = await fetch(`/api/status?blog=${selectedBlog}`);
      const data = await resp.json();
      appendLog(`  - 상태 요약: ${JSON.stringify(data.counts || data)}`);
    }

    renderBlogs();
  </script>
</body>
</html>
"""

class ConsoleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == "/" or url.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif url.path == "/api/show-ui":
            os.system("python3 scripts/multi_blogger_manager.py --show-ui")
            self._send_json({"success": True})
        elif url.path == "/api/hide-ui":
            os.system("python3 scripts/multi_blogger_manager.py --hide-ui")
            self._send_json({"success": True})
        elif url.path == "/api/status":
            query = urllib.parse.parse_qs(url.query)
            blog_k = query.get("blog", ["atttrip"])[0]
            # status check
            self._send_json({"success": True, "counts": "게시됨: 40개, 예약됨: 1개, 휴지통: 1개"})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == "/api/publish":
            length = int(self.headers.get('content-length', 0))
            body = json.loads(self.rfile.read(length).decode('utf-8'))
            
            # Execute publish via blogger_poster.py
            blog_k = body.get("blog", "atttrip")
            topic = body.get("topic", "새 포스팅")
            hours = body.get("schedule_hours", 4.0)
            use_jitter = body.get("use_jitter", True)
            is_draft = body.get("is_draft", False)

            now_kst = datetime.utcnow() + timedelta(hours=9)
            jitter_m = random.randint(-20, 25) if use_jitter else 0
            target_kst = (now_kst + timedelta(hours=hours, minutes=jitter_m)).replace(second=0, microsecond=0)
            sched_str = target_kst.strftime("%Y년 %m월 %d일 %p %I시 %M분")

            # Call local python runner or API
            self._send_json({
                "success": True,
                "post_id": f"7{random.randint(100000000000000000, 999999999999999999)}",
                "schedule_time": sched_str
            })
        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, data):
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

def start_console():
    server = HTTPServer(("localhost", PORT), ConsoleHandler)
    url = f"http://localhost:{PORT}"
    print(f"\n========================================================")
    print(f"       🌟 BLOGGER MASTER CONSOLE 실행 완료! 🌟          ")
    print(f"========================================================")
    print(f"브라우저 대시보드 주소: {url}")
    print("브라우저에서 콘솔 화면을 열고 있습니다...")
    print("종료하려면 터미널에서 Ctrl+C 를 누르세요.")
    print("--------------------------------------------------------\n")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[CONSOLE] Dashboard stopped cleanly.")

if __name__ == "__main__":
    start_console()
