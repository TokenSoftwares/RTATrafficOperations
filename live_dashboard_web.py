"""Capstone monitoring dashboard for the AI Edge Mesh demo."""

from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify, render_template_string, send_from_directory

from demo_simulator import get_simulator


DEFAULT_PORT = 5002
BASE_DIR = Path(__file__).resolve().parent
INTERSECTIONS_FILE = BASE_DIR / "intersections.json"
DEMO_VIDEO = BASE_DIR / "assets" / "demo_traffic.mp4"

app = Flask(__name__)


def load_intersections() -> dict:
    return json.loads(INTERSECTIONS_FILE.read_text(encoding="utf-8"))


PAGE = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>RTA AI Edge Mesh — Operations Dashboard</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0a1017;
      --panel: #111b26;
      --panel-border: #243646;
      --text: #edf5fb;
      --muted: #93a9ba;
      --accent: #2f80ed;
      --green: #27ae60;
      --yellow: #f1c40f;
      --red: #e74c3c;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, "Segoe UI", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    .shell { max-width: 1440px; margin: 0 auto; padding: 20px 24px 28px; }
    .header {
      display: flex; justify-content: space-between; align-items: flex-end;
      gap: 16px; margin-bottom: 18px; flex-wrap: wrap;
    }
    .header h1 { margin: 0; font-size: 1.55rem; letter-spacing: -0.02em; }
    .header .sub { color: var(--muted); font-size: 0.92rem; margin-top: 4px; }
    .badge {
      padding: 8px 12px; border-radius: 999px; background: #172433;
      border: 1px solid var(--panel-border); color: #b8d4ea; font-size: 0.82rem;
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }
    .stat-card {
      background: var(--panel);
      border: 1px solid var(--panel-border);
      border-radius: 14px;
      padding: 14px 16px;
      transition: border-color 0.25s ease, transform 0.25s ease;
    }
    .stat-card:hover { border-color: #355066; transform: translateY(-1px); }
    .stat-label { color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; }
    .stat-value { font-size: 1.45rem; font-weight: 800; margin-top: 6px; }
    .controls { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 14px; align-items: center; }
    button {
      border: 0; border-radius: 10px; padding: 10px 14px;
      background: var(--accent); color: white; font-weight: 700; cursor: pointer;
      transition: opacity 0.2s ease, transform 0.2s ease;
    }
    button:hover { opacity: 0.92; transform: translateY(-1px); }
    button.active { background: var(--green); }
    button.view-toggle.active { background: #7d5ba6; }
    .panel {
      background: var(--panel);
      border: 1px solid var(--panel-border);
      border-radius: 16px;
      padding: 16px;
    }
    .panel-title { font-size: 1rem; font-weight: 800; margin-bottom: 10px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
    .layout-main {
      display: grid;
      grid-template-columns: 1fr 320px;
      gap: 16px;
      align-items: start;
    }
    @media (max-width: 1100px) { .layout-main { grid-template-columns: 1fr; } }
    .pill {
      display: inline-block; padding: 4px 10px; border-radius: 999px;
      font-size: 12px; font-weight: 700;
    }
    .pill-green { background: #1f4d2d; color: #9be7b1; }
    .pill-yellow { background: #5a4a12; color: #ffe08a; }
    .pill-red { background: #5a1f1f; color: #ffb3b3; }
    .pill-approved { background: #1f4d2d; color: #9be7b1; }
    .pill-rejected { background: #5a1f1f; color: #ffb3b3; }
    .pill-pending { background: #334155; color: #cbd5e1; }
    .node-card { line-height: 1.55; font-size: 0.92rem; }
    .node-card .line { margin: 6px 0; color: #c8d7e2; }
    .node-card strong { color: #fff; }
    .event-log {
      max-height: 420px;
      overflow-y: auto;
      font-size: 0.86rem;
      line-height: 1.45;
    }
    .event-item {
      padding: 10px 0;
      border-bottom: 1px solid #1d2b38;
      animation: fadeIn 0.35s ease;
    }
    .event-time { color: #7fa6bf; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    .event-text { color: #dbe8f2; margin-top: 2px; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: none; } }
    #mapView { display: none; }
    #map { height: 560px; border-radius: 14px; border: 1px solid var(--panel-border); }
    .leaflet-popup-content-wrapper,
    .leaflet-popup-tip { background: #111b26; color: var(--text); }
    .popup-title { font-weight: 800; font-size: 15px; margin-bottom: 10px; }
    .popup-row {
      display: flex; justify-content: space-between; gap: 12px;
      padding: 5px 0; border-bottom: 1px solid #1d2b38; font-size: 13px;
    }
    .popup-row:last-child { border-bottom: 0; }
    .popup-label { color: var(--muted); }
    .popup-value { text-align: right; font-weight: 600; }
    .traffic-light-icon { background: transparent; border: none; }
    .tl-wrap {
      width: 34px; height: 76px; border-radius: 10px;
      background: #1a2530; border: 2px solid #5d7386;
      display: flex; flex-direction: column; align-items: center;
      justify-content: space-around; padding: 6px 0;
      box-shadow: 0 4px 14px rgba(0,0,0,0.35);
      transition: box-shadow 0.3s ease;
    }
    .tl-wrap.corridor-active { box-shadow: 0 0 16px rgba(39,174,96,0.75); border-color: #27ae60; }
    .tl-lamp {
      width: 16px; height: 16px; border-radius: 50%;
      background: #2a3642; opacity: 0.35;
      transition: opacity 0.25s ease, box-shadow 0.25s ease;
    }
    .tl-lamp.on-red { background: var(--red); opacity: 1; box-shadow: 0 0 10px rgba(231,76,60,0.8); }
    .tl-lamp.on-yellow { background: var(--yellow); opacity: 1; box-shadow: 0 0 10px rgba(241,196,15,0.8); }
    .tl-lamp.on-green { background: var(--green); opacity: 1; box-shadow: 0 0 10px rgba(39,174,96,0.85); }
    .ambulance-icon {
      font-size: 28px;
      line-height: 28px;
      text-align: center;
      filter: drop-shadow(0 2px 4px rgba(0,0,0,0.45));
    }
    .node-card.clickable {
      cursor: pointer;
      transition: border-color 0.25s ease, transform 0.25s ease, box-shadow 0.25s ease;
    }
    .node-card.clickable:hover {
      border-color: #3d6a8a;
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.28);
    }
    .node-card .open-hint {
      margin-top: 10px;
      font-size: 0.78rem;
      color: #6fa3c4;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .cctv-modal {
      position: fixed;
      inset: 0;
      z-index: 10000;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
      background: rgba(4, 8, 14, 0.82);
      backdrop-filter: blur(8px);
      opacity: 0;
      visibility: hidden;
      transition: opacity 0.32s ease, visibility 0.32s ease;
    }
    .cctv-modal.open { opacity: 1; visibility: visible; }
    .cctv-panel {
      width: min(980px, 100%);
      max-height: calc(100vh - 48px);
      overflow: auto;
      background: linear-gradient(180deg, #121c28 0%, #0d1520 100%);
      border: 1px solid #2f4558;
      border-radius: 18px;
      box-shadow: 0 28px 80px rgba(0,0,0,0.55);
      transform: scale(0.96) translateY(14px);
      transition: transform 0.32s cubic-bezier(0.22, 1, 0.36, 1);
    }
    .cctv-modal.open .cctv-panel { transform: none; }
    .cctv-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
      padding: 18px 20px 14px;
      border-bottom: 1px solid #1f2f3d;
    }
    .cctv-header h2 { margin: 0; font-size: 1.15rem; }
    .cctv-header .sub { color: var(--muted); font-size: 0.86rem; margin-top: 4px; }
    .cctv-close {
      width: auto;
      padding: 8px 14px;
      background: #243646;
      border-radius: 8px;
      font-size: 0.85rem;
    }
    .cctv-body {
      display: grid;
      grid-template-columns: 1.4fr 0.9fr;
      gap: 16px;
      padding: 16px 20px 20px;
    }
    @media (max-width: 860px) { .cctv-body { grid-template-columns: 1fr; } }
    .cctv-feed-wrap {
      position: relative;
      border-radius: 12px;
      overflow: hidden;
      border: 1px solid #2a3f52;
      background: #060a10;
      aspect-ratio: 16 / 9;
    }
    .cctv-feed-wrap video {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
    .cctv-overlay-top {
      position: absolute;
      top: 0; left: 0; right: 0;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      padding: 12px 14px;
      background: linear-gradient(180deg, rgba(0,0,0,0.65), transparent);
      pointer-events: none;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
    }
    .cctv-live {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 999px;
      background: rgba(231, 76, 60, 0.18);
      border: 1px solid rgba(231, 76, 60, 0.45);
      color: #ffb3b3;
      font-weight: 700;
    }
    .cctv-live-dot {
      width: 8px; height: 8px; border-radius: 50%;
      background: var(--red);
      animation: recBlink 1.2s ease-in-out infinite;
    }
    @keyframes recBlink { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
    .cctv-overlay-bottom {
      position: absolute;
      bottom: 0; left: 0; right: 0;
      padding: 10px 14px;
      background: linear-gradient(0deg, rgba(0,0,0,0.72), transparent);
      pointer-events: none;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 11px;
      color: #c8d7e2;
    }
    .fake-box {
      position: absolute;
      border: 2px solid rgba(39, 174, 96, 0.85);
      box-shadow: 0 0 12px rgba(39, 174, 96, 0.25);
      pointer-events: none;
    }
    .fake-box-label {
      position: absolute;
      top: -18px; left: -2px;
      padding: 1px 6px;
      background: rgba(39, 174, 96, 0.88);
      color: #06210f;
      font-size: 10px;
      font-weight: 700;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      white-space: nowrap;
    }
    .cctv-stats { display: grid; gap: 10px; align-content: start; }
    .cctv-stat {
      padding: 12px 14px;
      border-radius: 12px;
      background: rgba(10, 18, 26, 0.9);
      border: 1px solid #223544;
    }
    .cctv-stat-label {
      color: var(--muted);
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .cctv-stat-value {
      margin-top: 4px;
      font-size: 1.05rem;
      font-weight: 700;
    }
  </style>
</head>
<body>
  <div class="shell">
    <div class="header">
      <div>
        <h1>RTA AI Edge Mesh Operations Dashboard</h1>
        <div class="sub">Central monitoring view — the hub observes only and never controls signals directly.</div>
      </div>
      <div class="badge" id="liveBadge">Live simulation</div>
    </div>

    <div class="stats" id="statsBar"></div>

    <div class="controls">
      <button id="btnDashboard" class="view-toggle active" onclick="showView('dashboard')">Dashboard View</button>
      <button id="btnMap" class="view-toggle" onclick="showView('map')">Live Map View</button>
    </div>

    <div id="scenarioInfo" class="panel" style="margin-bottom:14px;"></div>
    <div id="scenarioButtons" class="controls" style="margin-top:0;"></div>

    <div class="layout-main">
      <div>
        <div id="dashboardView">
          <div id="intersections" class="grid"></div>
        </div>
        <div id="mapView">
          <div class="panel" style="margin-bottom:12px;">
            <div class="panel-title">Live Corridor Map</div>
            <div id="mapLegend" class="sub" style="margin:0;color:var(--muted);"></div>
          </div>
          <div id="map"></div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-title">Live Event Log</div>
        <div id="eventLog" class="event-log"></div>
      </div>
    </div>
  </div>

  <div id="cctvModal" class="cctv-modal" onclick="if (event.target === this) closeCctvModal()">
    <div class="cctv-panel" role="dialog" aria-modal="true" aria-labelledby="cctvTitle">
      <div class="cctv-header">
        <div>
          <h2 id="cctvTitle">CCTV Feed</h2>
          <div class="sub" id="cctvSubtitle">Intersection camera</div>
        </div>
        <button type="button" class="cctv-close" onclick="closeCctvModal()">Close</button>
      </div>
      <div class="cctv-body">
        <div class="cctv-feed-wrap">
          <video id="cctvVideo" muted loop playsinline></video>
          <div id="cctvFakeBoxes"></div>
          <div class="cctv-overlay-top">
            <div>
              <div id="cctvCameraId">CAM-J1</div>
              <div id="cctvFeedTime">--:--:--</div>
            </div>
            <div class="cctv-live"><span class="cctv-live-dot"></span>LIVE</div>
          </div>
          <div class="cctv-overlay-bottom" id="cctvFeedLabel">RTA Edge Mesh — AI Camera Feed</div>
        </div>
        <div class="cctv-stats">
          <div class="cctv-stat"><div class="cctv-stat-label">Intersection</div><div class="cctv-stat-value" id="cctvStatName">—</div></div>
          <div class="cctv-stat"><div class="cctv-stat-label">Current Signal</div><div class="cctv-stat-value" id="cctvStatSignal">—</div></div>
          <div class="cctv-stat"><div class="cctv-stat-label">Vehicles Detected</div><div class="cctv-stat-value" id="cctvStatVehicles">—</div></div>
          <div class="cctv-stat"><div class="cctv-stat-label">Queue Length</div><div class="cctv-stat-value" id="cctvStatQueue">—</div></div>
          <div class="cctv-stat"><div class="cctv-stat-label">Congestion</div><div class="cctv-stat-value" id="cctvStatCongestion">—</div></div>
          <div class="cctv-stat"><div class="cctv-stat-label">Safety Status</div><div class="cctv-stat-value" id="cctvStatSafety">—</div></div>
          <div class="cctv-stat"><div class="cctv-stat-label">AI Recommendation</div><div class="cctv-stat-value" id="cctvStatDecision" style="font-size:0.92rem;line-height:1.4;">—</div></div>
        </div>
      </div>
    </div>
  </div>

  <script>
    const statsBar = document.getElementById('statsBar');
    const scenarioButtons = document.getElementById('scenarioButtons');
    const scenarioInfo = document.getElementById('scenarioInfo');
    const intersectionsEl = document.getElementById('intersections');
    const eventLogEl = document.getElementById('eventLog');
    const dashboardView = document.getElementById('dashboardView');
    const mapView = document.getElementById('mapView');
    const btnDashboard = document.getElementById('btnDashboard');
    const btnMap = document.getElementById('btnMap');

    let activeScenario = null;
    let mapData = null;
    let mapInstance = null;
    let markers = {};
    let staticLines = {};
    let routeGlowLine = null;
    let corridorGlowLine = null;
    let ambulanceMarker = null;
    let mapInitialized = false;

    let lastStateSignature = '';
    let seenEventMeshIds = new Set();
    let seenPulseMeshIds = new Set();
    let latestState = null;
    let meshTotal = 0;
    let emergencyTotal = 0;
    let events = [];
    let previousNodeState = {};

    let emergencyAnimating = false;
    let emergencyStartTime = 0;
    let emergencyDurationMs = 14000;
    let signalOverrides = {};
    let corridorActiveSet = new Set();
    let animFrameId = null;

    const CCTV_VIDEO_SRC = '/assets/demo_traffic.mp4';
    const CCTV_START_OFFSETS = { J1: 0, J2: 12, J3: 24 };
    const FAKE_BOX_LAYOUT = [
      { left: '12%', top: '48%', width: '18%', height: '22%', label: 'car 0.91' },
      { left: '34%', top: '52%', width: '16%', height: '20%', label: 'car 0.87' },
      { left: '56%', top: '44%', width: '20%', height: '24%', label: 'truck 0.84' },
      { left: '72%', top: '58%', width: '14%', height: '18%', label: 'car 0.79' },
      { left: '22%', top: '62%', width: '15%', height: '19%', label: 'bus 0.76' },
      { left: '48%', top: '36%', width: '13%', height: '17%', label: 'car 0.73' },
    ];
    let cctvOpenNodeId = null;
    let cctvClockTimer = null;

    function pill(color) {
      const cls = color === 'GREEN' ? 'pill-green' : color === 'YELLOW' ? 'pill-yellow' : 'pill-red';
      return `<span class="pill ${cls}">${color}</span>`;
    }

    function safetyPill(status) {
      const cls = status === 'APPROVED' ? 'pill-approved' : status === 'REJECTED' ? 'pill-rejected' : 'pill-pending';
      return `<span class="pill ${cls}">${status}</span>`;
    }

    function totalQueueLength(queueLengths) {
      if (!queueLengths) return 0;
      return Object.values(queueLengths).reduce((sum, value) => sum + value, 0);
    }

    function congestionScore(level) {
      return { LOW: 1, MEDIUM: 2, HIGH: 3 }[level] || 1;
    }

    function congestionLabel(score) {
      if (score >= 2.4) return 'HIGH';
      if (score >= 1.6) return 'MEDIUM';
      return 'LOW';
    }

    function nowTime() {
      return new Date().toLocaleTimeString('en-GB', { hour12: false });
    }

    function pushEvent(text) {
      events.unshift({ time: nowTime(), text });
      if (events.length > 60) events.length = 60;
      renderEventLog();
    }

    function renderEventLog() {
      eventLogEl.innerHTML = events.length
        ? events.map(e => `<div class="event-item"><div class="event-time">${e.time}</div><div class="event-text">${e.text}</div></div>`).join('')
        : '<div class="event-item"><div class="event-text">Waiting for simulation events…</div></div>';
    }

    function latestDecision(node) {
      const detail = node.safety_detail;
      if (!detail) return 'Pending review';
      if (detail.status === 'APPROVED') {
        return `Green for ${detail.approved_phase} (${detail.approved_green_duration_s}s)`;
      }
      return detail.reason || 'Rejected by Safety Kernel';
    }

    function emergencyStatus(node) {
      if (node.emergency_alerts && node.emergency_alerts.length) {
        return node.emergency_alerts.map(a => `${a.source_node}: ${a.reason}`).join('; ');
      }
      return 'None active';
    }

    function neighborNames(nodeId) {
      const meta = mapData.intersections.find(item => item.id === nodeId);
      if (!meta) return 'None';
      return meta.neighbors.map(id => {
        const n = mapData.intersections.find(item => item.id === id);
        return n ? n.id : id;
      }).join(', ');
    }

    function intersectionMeta(nodeId) {
      return mapData && mapData.intersections.find(item => item.id === nodeId);
    }

    function intersectionNode(nodeId) {
      if (!latestState) return null;
      return latestState.intersections.find(node => node.node_id === nodeId) || null;
    }

    function renderFakeDetectionBoxes(count) {
      const container = document.getElementById('cctvFakeBoxes');
      const total = Math.max(0, Math.min(count || 0, FAKE_BOX_LAYOUT.length));
      container.innerHTML = FAKE_BOX_LAYOUT.slice(0, total).map(box => `
        <div class="fake-box" style="left:${box.left};top:${box.top};width:${box.width};height:${box.height};">
          <div class="fake-box-label">${box.label}</div>
        </div>
      `).join('');
    }

    function updateCctvModalStats() {
      if (!cctvOpenNodeId) return;
      const meta = intersectionMeta(cctvOpenNodeId);
      const node = intersectionNode(cctvOpenNodeId);
      if (!meta || !node) return;

      document.getElementById('cctvTitle').textContent = `${meta.id} — Live CCTV`;
      document.getElementById('cctvSubtitle').textContent = meta.name;
      document.getElementById('cctvCameraId').textContent = `CAM-${meta.id}`;
      document.getElementById('cctvFeedLabel').textContent = `${meta.name} | RTA Edge Mesh AI Camera`;
      document.getElementById('cctvStatName').textContent = meta.name;
      document.getElementById('cctvStatSignal').innerHTML = pill(displaySignal(node));
      document.getElementById('cctvStatVehicles').textContent = node.vehicle_count;
      document.getElementById('cctvStatQueue').textContent = totalQueueLength(node.queue_lengths);
      document.getElementById('cctvStatCongestion').textContent = node.congestion_level;
      document.getElementById('cctvStatSafety').innerHTML = safetyPill(node.safety_status);
      document.getElementById('cctvStatDecision').textContent = latestDecision(node);
      renderFakeDetectionBoxes(node.vehicle_count);
    }

    function startCctvClock() {
      if (cctvClockTimer) clearInterval(cctvClockTimer);
      const tick = () => {
        document.getElementById('cctvFeedTime').textContent = nowTime();
      };
      tick();
      cctvClockTimer = setInterval(tick, 1000);
    }

    function stopCctvClock() {
      if (cctvClockTimer) clearInterval(cctvClockTimer);
      cctvClockTimer = null;
    }

    function openCctvModal(nodeId) {
      const meta = intersectionMeta(nodeId);
      if (!meta) return;

      cctvOpenNodeId = nodeId;
      const modal = document.getElementById('cctvModal');
      const video = document.getElementById('cctvVideo');
      const offset = CCTV_START_OFFSETS[nodeId] || 0;

      video.src = CCTV_VIDEO_SRC;
      video.onloadedmetadata = () => {
        video.currentTime = offset;
        video.play().catch(() => {});
      };
      if (video.readyState >= 1) {
        video.currentTime = offset;
        video.play().catch(() => {});
      }

      updateCctvModalStats();
      startCctvClock();
      modal.classList.add('open');
      document.body.style.overflow = 'hidden';
      pushEvent(`CCTV feed opened for ${nodeId}`);
    }

    function closeCctvModal() {
      const modal = document.getElementById('cctvModal');
      const video = document.getElementById('cctvVideo');
      modal.classList.remove('open');
      document.body.style.overflow = '';
      stopCctvClock();
      video.pause();
      video.removeAttribute('src');
      video.load();
      document.getElementById('cctvFakeBoxes').innerHTML = '';
      cctvOpenNodeId = null;
    }

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && cctvOpenNodeId) closeCctvModal();
    });

    function showView(view) {
      const isDashboard = view === 'dashboard';
      dashboardView.style.display = isDashboard ? 'grid' : 'none';
      mapView.style.display = isDashboard ? 'none' : 'block';
      btnDashboard.classList.toggle('active', isDashboard);
      btnMap.classList.toggle('active', !isDashboard);
      if (!isDashboard && mapInstance) setTimeout(() => mapInstance.invalidateSize(), 120);
    }

    async function setScenario(key) {
      await fetch('/api/scenario/' + key, { method: 'POST' });
      seenEventMeshIds.clear();
      seenPulseMeshIds.clear();
      stopEmergencyAnimation(true);
      await refresh();
      if (key === 'emergency_vehicle') startEmergencyAnimation();
    }

    function trafficLightHtml(color, corridorActive) {
      const red = color === 'RED' ? 'on-red' : '';
      const yellow = color === 'YELLOW' ? 'on-yellow' : '';
      const green = color === 'GREEN' ? 'on-green' : '';
      const wrapClass = corridorActive ? 'tl-wrap corridor-active' : 'tl-wrap';
      return `<div class="${wrapClass}"><div class="tl-lamp ${red}"></div><div class="tl-lamp ${yellow}"></div><div class="tl-lamp ${green}"></div></div>`;
    }

    function makeTrafficLightIcon(color, corridorActive) {
      return L.divIcon({
        className: 'traffic-light-icon',
        html: trafficLightHtml(color, corridorActive),
        iconSize: [34, 76],
        iconAnchor: [17, 38],
        popupAnchor: [0, -36],
      });
    }

    function edgeKey(a, b) { return [a, b].sort().join('--'); }

    function routeCoords() {
      return (mapData.emergency_route || []).map(id => {
        const item = mapData.intersections.find(x => x.id === id);
        return item ? [item.lat, item.lng] : null;
      }).filter(Boolean);
    }

    function initMap() {
      if (mapInitialized) return;
      mapInstance = L.map('map', { zoomControl: true }).setView([25.2085, 55.2745], 15);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
      }).addTo(mapInstance);

      mapData.intersections.forEach(meta => {
        const icon = makeTrafficLightIcon('RED', false);
        const marker = L.marker([meta.lat, meta.lng], { icon, zIndexOffset: 500 }).addTo(mapInstance);
        marker.on('click', () => openCctvModal(meta.id));
        markers[meta.id] = marker;
      });

      const drawn = new Set();
      mapData.intersections.forEach(meta => {
        meta.neighbors.forEach(neighborId => {
          const key = edgeKey(meta.id, neighborId);
          if (drawn.has(key)) return;
          drawn.add(key);
          const neighbor = mapData.intersections.find(item => item.id === neighborId);
          if (!neighbor) return;
          staticLines[key] = L.polyline(
            [[meta.lat, meta.lng], [neighbor.lat, neighbor.lng]],
            { color: '#4d6578', weight: 3, opacity: 0.55 }
          ).addTo(mapInstance);
        });
      });

      const coords = routeCoords();
      if (coords.length >= 2) {
        routeGlowLine = L.polyline(coords, { color: '#35506a', weight: 6, opacity: 0.35 }).addTo(mapInstance);
      }

      mapInitialized = true;
    }

    function animatePulse(sourceId, targetId, messageType) {
      const source = mapData.intersections.find(item => item.id === sourceId);
      const target = mapData.intersections.find(item => item.id === targetId);
      if (!source || !target || !mapInstance) return;

      const color = messageType === 'EMERGENCY_BROADCAST' ? '#e74c3c' : '#3498db';
      const start = { lat: source.lat, lng: source.lng };
      const end = { lat: target.lat, lng: target.lng };
      const started = performance.now();
      const duration = 800;

      const pulseIcon = L.divIcon({
        className: 'traffic-light-icon',
        html: `<div style="width:14px;height:14px;border-radius:50%;background:${color};box-shadow:0 0 12px ${color};"></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      });
      const pulseMarker = L.marker([start.lat, start.lng], { icon: pulseIcon, zIndexOffset: 900 }).addTo(mapInstance);

      function frame(now) {
        const t = Math.min(1, (now - started) / duration);
        const lat = start.lat + (end.lat - start.lat) * t;
        const lng = start.lng + (end.lng - start.lng) * t;
        pulseMarker.setLatLng([lat, lng]);
        if (t < 1) requestAnimationFrame(frame);
        else mapInstance.removeLayer(pulseMarker);
      }
      requestAnimationFrame(frame);
    }

    function interpolateRoute(progress) {
      const coords = routeCoords();
      if (coords.length < 2) return coords[0] || [25.2085, 55.2745];
      const scaled = progress * (coords.length - 1);
      const idx = Math.min(coords.length - 2, Math.floor(scaled));
      const t = scaled - idx;
      const a = coords[idx], b = coords[idx + 1];
      return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
    }

    function refreshCorridorMarkers() {
      if (!latestState || !mapData) return;
      const nodeById = Object.fromEntries(latestState.intersections.map(node => [node.node_id, node]));
      mapData.intersections.forEach(meta => {
        const node = nodeById[meta.id];
        if (!node || !markers[meta.id]) return;
        const color = displaySignal(node);
        markers[meta.id].setIcon(makeTrafficLightIcon(color, corridorActiveSet.has(meta.id)));
      });
    }

    function stopEmergencyAnimation(silent=false) {
      emergencyAnimating = false;
      if (animFrameId) cancelAnimationFrame(animFrameId);
      animFrameId = null;
      signalOverrides = {};
      corridorActiveSet.clear();
      if (ambulanceMarker && mapInstance) {
        mapInstance.removeLayer(ambulanceMarker);
        ambulanceMarker = null;
      }
      if (corridorGlowLine && mapInstance) {
        mapInstance.removeLayer(corridorGlowLine);
        corridorGlowLine = null;
      }
      if (!silent) pushEvent('Emergency corridor animation stopped');
    }

    function startEmergencyAnimation() {
      if (!mapInstance || !mapData) return;
      stopEmergencyAnimation(true);
      emergencyAnimating = true;
      emergencyStartTime = performance.now();
      pushEvent('Green corridor activated');

      const ambIcon = L.divIcon({
        className: 'traffic-light-icon',
        html: '<div class="ambulance-icon">🚑</div>',
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });
      const start = interpolateRoute(0);
      ambulanceMarker = L.marker(start, { icon: ambIcon, zIndexOffset: 1200 }).addTo(mapInstance);

      function tick(now) {
        if (!emergencyAnimating || activeScenario !== 'emergency_vehicle') return;
        const elapsed = now - emergencyStartTime;
        let progress = (elapsed % emergencyDurationMs) / emergencyDurationMs;

        const pos = interpolateRoute(progress);
        ambulanceMarker.setLatLng(pos);

        const routeIds = mapData.emergency_route || [];
        signalOverrides = {};
        corridorActiveSet.clear();
        routeIds.forEach((id, index) => {
          const threshold = index / Math.max(1, routeIds.length - 1);
          const release = threshold + 0.18;
          if (progress + 0.001 >= threshold && progress < release + 0.08) {
            signalOverrides[id] = 'GREEN';
            corridorActiveSet.add(id);
          }
        });

        const glowCoords = routeCoords().slice(0, Math.max(2, Math.ceil(progress * (routeCoords().length - 1)) + 1));
        if (corridorGlowLine) mapInstance.removeLayer(corridorGlowLine);
        if (glowCoords.length >= 2) {
          corridorGlowLine = L.polyline(glowCoords, {
            color: '#27ae60', weight: 8, opacity: 0.78
          }).addTo(mapInstance);
        }

        refreshCorridorMarkers();

        animFrameId = requestAnimationFrame(tick);
      }
      animFrameId = requestAnimationFrame(tick);
    }

    function displaySignal(node) {
      if (signalOverrides[node.node_id]) return signalOverrides[node.node_id];
      return node.signal_color;
    }

    function updateMap(data) {
      if (!mapData) return;
      initMap();

      const nodeById = Object.fromEntries(data.intersections.map(node => [node.node_id, node]));
      mapData.intersections.forEach(meta => {
        const node = nodeById[meta.id];
        if (!node) return;
        const color = displaySignal(node);
        const corridorActive = corridorActiveSet.has(meta.id);
        markers[meta.id].setIcon(makeTrafficLightIcon(color, corridorActive));
      });

      data.mesh_messages.forEach(message => {
        const id = message.message_id || `${message.source_node}-${message.target_node}-${message.message_type}-${message.sent_at}`;
        if (seenPulseMeshIds.has(id)) return;
        seenPulseMeshIds.add(id);
        if (message.message_type === 'QUEUE_UPDATE' || message.message_type === 'EMERGENCY_BROADCAST') {
          animatePulse(message.source_node, message.target_node, message.message_type);
        }
      });

      document.getElementById('mapLegend').textContent =
        `${mapData.corridor_name} | ${data.scenario.title} | Tick ${data.tick_count}`;
    }

    function computeStats(data) {
      const nodes = data.intersections;
      const vehicles = nodes.reduce((sum, n) => sum + n.vehicle_count, 0);
      const avgQueue = nodes.length
        ? nodes.reduce((sum, n) => sum + totalQueueLength(n.queue_lengths), 0) / nodes.length
        : 0;
      const avgCongScore = nodes.length
        ? nodes.reduce((sum, n) => sum + congestionScore(n.congestion_level), 0) / nodes.length
        : 1;
      const approved = nodes.filter(n => n.safety_status === 'APPROVED').length;
      const emergencies = nodes.reduce((sum, n) => sum + (n.emergency_alerts ? n.emergency_alerts.length : 0), 0);
      return { vehicles, avgQueue, avgCong: congestionLabel(avgCongScore), meshTotal, approved, emergencies };
    }

    function renderStats(data) {
      const s = computeStats(data);
      const cards = [
        ['Vehicles Detected', s.vehicles],
        ['Average Queue Length', s.avgQueue.toFixed(1)],
        ['Average Congestion', s.avgCong],
        ['Mesh Messages Sent', s.meshTotal],
        ['Safety Decisions Approved', s.approved],
        ['Emergency Events', s.emergencies + emergencyTotal],
      ];
      statsBar.innerHTML = cards.map(([label, value]) => `
        <div class="stat-card"><div class="stat-label">${label}</div><div class="stat-value">${value}</div></div>
      `).join('');
    }

    function detectEvents(data) {
      if (data.scenario.key !== activeScenario) {
        pushEvent(`Scenario switched to ${data.scenario.title}`);
      }

      data.mesh_messages.forEach(message => {
        const id = message.message_id || `${message.source_node}-${message.target_node}-${message.message_type}-${message.sent_at}`;
        if (seenEventMeshIds.has(id)) return;
        seenEventMeshIds.add(id);
        meshTotal += 1;
        if (message.message_type === 'QUEUE_UPDATE') {
          pushEvent(`Queue update from ${message.source_node} to ${message.target_node}`);
        } else if (message.message_type === 'EMERGENCY_BROADCAST') {
          emergencyTotal += 1;
          pushEvent(`Emergency broadcast sent by ${message.source_node}`);
        } else if (message.message_type) {
          pushEvent(`Mesh ${message.message_type} between ${message.source_node || message.node_id} and ${message.target_node || 'peer'}`);
        }
      });

      data.intersections.forEach(node => {
        const prev = previousNodeState[node.node_id] || {};
        const signature = JSON.stringify({
          safety: node.safety_status,
          phase: node.active_phase,
          decision: latestDecision(node),
        });
        if (prev.signature !== signature) {
          if (node.safety_status === 'APPROVED') {
            pushEvent(`Safety approved at ${node.node_id}`);
            pushEvent(`Signal optimized at ${node.node_id} — ${latestDecision(node)}`);
          } else if (node.safety_status === 'REJECTED') {
            pushEvent(`Safety rejected at ${node.node_id}`);
          }
        }
        previousNodeState[node.node_id] = { signature };
      });
    }

    function renderDashboard(data) {
      activeScenario = data.scenario.key;
      scenarioInfo.innerHTML = `<strong>${data.scenario.title}</strong><br><span style="color:var(--muted)">${data.scenario.description}</span><br>Simulation tick: ${data.tick_count}`;
      scenarioButtons.innerHTML = data.scenarios.map(s => `
        <button class="${s.key === activeScenario ? 'active' : ''}" onclick="setScenario('${s.key}')">${s.title}</button>
      `).join('');

      intersectionsEl.innerHTML = data.intersections.map(node => {
        const meta = mapData.intersections.find(x => x.id === node.node_id);
        const name = meta ? meta.name : node.node_id;
        return `
          <div class="panel node-card clickable" onclick="openCctvModal('${node.node_id}')">
            <div class="panel-title">${name}</div>
            <div class="line">Signal: ${pill(node.signal_color)} &nbsp; Phase: <strong>${node.active_phase || 'n/a'}</strong></div>
            <div class="line">Vehicles: <strong>${node.vehicle_count}</strong> &nbsp; Queue: <strong>${totalQueueLength(node.queue_lengths)}</strong></div>
            <div class="line">Congestion: <strong>${node.congestion_level}</strong></div>
            <div class="line">Safety: ${safetyPill(node.safety_status)}</div>
            <div class="line">Latest decision: <strong>${latestDecision(node)}</strong></div>
            <div class="line">Emergency: <strong>${emergencyStatus(node)}</strong></div>
            <div class="line">Neighbors: <strong>${neighborNames(node.node_id)}</strong></div>
            <div class="open-hint">Click to open CCTV feed</div>
          </div>
        `;
      }).join('');
    }

    function render(data) {
      latestState = data;
      detectEvents(data);
      renderStats(data);
      renderDashboard(data);
      updateMap(data);

      if (data.scenario.key === 'emergency_vehicle' && !emergencyAnimating) {
        startEmergencyAnimation();
      }
      if (data.scenario.key !== 'emergency_vehicle' && emergencyAnimating) {
        stopEmergencyAnimation(true);
      }

      document.getElementById('liveBadge').textContent = `Live | Tick ${data.tick_count} | ${data.scenario.title}`;
      updateCctvModalStats();
    }

    async function refresh() {
      const response = await fetch('/api/state');
      render(await response.json());
    }

    async function bootstrap() {
      renderEventLog();
      const response = await fetch('/api/intersections');
      mapData = await response.json();
      pushEvent('Operations dashboard connected');
      await refresh();
      setInterval(refresh, 2000);
    }

    bootstrap();
  </script>
</body>
</html>
"""


@app.get("/")
def index():
    return render_template_string(PAGE)


@app.get("/api/intersections")
def api_intersections():
    return jsonify(load_intersections())


@app.get("/assets/demo_traffic.mp4")
def demo_traffic_video():
    if not DEMO_VIDEO.exists():
        return jsonify({"error": "Demo video not found."}), 404
    return send_from_directory(DEMO_VIDEO.parent, DEMO_VIDEO.name)


@app.get("/api/state")
def api_state():
    return jsonify(get_simulator().dashboard_state())


@app.post("/api/scenario/<scenario_key>")
def api_set_scenario(scenario_key: str):
    try:
        scenario = get_simulator().set_scenario(scenario_key)
    except KeyError:
        return jsonify({"error": f"Unknown scenario: {scenario_key}"}), 404
    return jsonify(
        {
            "ok": True,
            "scenario": {
                "key": scenario.key.value,
                "title": scenario.title,
                "description": scenario.description,
            },
        }
    )


def main() -> None:
    simulator = get_simulator()
    simulator.start(interval_s=2.0)
    print(f"AI Edge Mesh demo running: http://127.0.0.1:{DEFAULT_PORT}")
    print("Switch scenarios from the dashboard during the presentation.")
    app.run(host="127.0.0.1", port=DEFAULT_PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
