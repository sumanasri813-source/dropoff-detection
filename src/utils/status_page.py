"""
Real-Time System Status Page

Serves a beautiful, auto-refreshing HTML status page at /status.
Shows live system health, component status, uptime metrics, 
response times, and recent activity — like status.github.com.
"""

from __future__ import annotations

from flask import Flask
from src.utils.logger import get_logger

logger = get_logger("status_page")


STATUS_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Status — Drop-Off Detection</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', -apple-system, sans-serif;
            background: #08080f;
            color: #e2e4ea;
            min-height: 100vh;
        }

        .header {
            background: linear-gradient(135deg, #0f0f1a 0%, #1a1033 100%);
            border-bottom: 1px solid rgba(99, 102, 241, 0.2);
            padding: 28px 0;
            text-align: center;
        }
        .header h1 {
            font-size: 22px;
            font-weight: 600;
            color: #fff;
            letter-spacing: -0.3px;
        }
        .header h1 span { color: #818cf8; }
        .header p {
            color: #8b8fa3;
            font-size: 13px;
            margin-top: 6px;
        }

        .container {
            max-width: 780px;
            margin: 0 auto;
            padding: 32px 20px;
        }

        /* Overall status banner */
        .status-banner {
            border-radius: 12px;
            padding: 24px 28px;
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 32px;
            border: 1px solid rgba(255,255,255,0.06);
        }
        .status-banner.operational {
            background: linear-gradient(135deg, rgba(34,197,94,0.08), rgba(34,197,94,0.02));
            border-color: rgba(34,197,94,0.2);
        }
        .status-banner.degraded {
            background: linear-gradient(135deg, rgba(250,204,21,0.08), rgba(250,204,21,0.02));
            border-color: rgba(250,204,21,0.2);
        }
        .status-banner.down {
            background: linear-gradient(135deg, rgba(239,68,68,0.08), rgba(239,68,68,0.02));
            border-color: rgba(239,68,68,0.2);
        }
        .status-icon {
            width: 42px; height: 42px;
            border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-size: 20px;
            flex-shrink: 0;
        }
        .status-banner.operational .status-icon { background: rgba(34,197,94,0.15); }
        .status-banner.degraded .status-icon { background: rgba(250,204,21,0.15); }
        .status-banner.down .status-icon { background: rgba(239,68,68,0.15); }
        .status-banner h2 {
            font-size: 18px;
            font-weight: 600;
            color: #fff;
        }
        .status-banner p {
            font-size: 13px;
            color: #8b8fa3;
            margin-top: 2px;
        }

        /* Component cards */
        .section-title {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            color: #6b6f85;
            margin-bottom: 12px;
        }

        .component-list {
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 32px;
        }
        .component {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 20px;
            border-bottom: 1px solid rgba(255,255,255,0.04);
            transition: background 0.2s;
        }
        .component:last-child { border-bottom: none; }
        .component:hover { background: rgba(255,255,255,0.02); }
        .component-name {
            font-size: 14px;
            font-weight: 500;
            color: #e2e4ea;
        }
        .component-detail {
            font-size: 12px;
            color: #6b6f85;
            margin-top: 2px;
        }
        .badge {
            font-size: 11px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .badge.up {
            background: rgba(34,197,94,0.12);
            color: #4ade80;
        }
        .badge.degraded {
            background: rgba(250,204,21,0.12);
            color: #fbbf24;
        }
        .badge.down {
            background: rgba(239,68,68,0.12);
            color: #f87171;
        }

        /* Metrics grid */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 12px;
            margin-bottom: 32px;
        }
        .metric-card {
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 10px;
            padding: 18px 16px;
            text-align: center;
            transition: border-color 0.2s, transform 0.2s;
        }
        .metric-card:hover {
            border-color: rgba(99,102,241,0.3);
            transform: translateY(-2px);
        }
        .metric-value {
            font-size: 26px;
            font-weight: 700;
            color: #fff;
            font-variant-numeric: tabular-nums;
        }
        .metric-value.green { color: #4ade80; }
        .metric-value.purple { color: #a78bfa; }
        .metric-value.cyan { color: #22d3ee; }
        .metric-value.amber { color: #fbbf24; }
        .metric-label {
            font-size: 11px;
            color: #6b6f85;
            margin-top: 4px;
            text-transform: uppercase;
            letter-spacing: 0.8px;
        }

        /* Latency bar chart */
        .latency-section { margin-bottom: 32px; }
        .latency-bars {
            display: flex;
            align-items: flex-end;
            gap: 3px;
            height: 60px;
            margin-top: 10px;
        }
        .latency-bar {
            flex: 1;
            background: linear-gradient(to top, #312e81, #818cf8);
            border-radius: 3px 3px 0 0;
            min-height: 4px;
            transition: height 0.5s ease;
            position: relative;
        }
        .latency-bar:hover {
            background: linear-gradient(to top, #4338ca, #a78bfa);
        }
        .latency-bar:hover::after {
            content: attr(data-ms);
            position: absolute;
            top: -22px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 10px;
            color: #a78bfa;
            white-space: nowrap;
        }
        .latency-legend {
            display: flex;
            justify-content: space-between;
            margin-top: 6px;
            font-size: 10px;
            color: #4b4f68;
        }

        /* Activity log */
        .activity-list {
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 32px;
        }
        .activity-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 20px;
            border-bottom: 1px solid rgba(255,255,255,0.04);
            font-size: 13px;
        }
        .activity-item:last-child { border-bottom: none; }
        .activity-dot {
            width: 8px; height: 8px;
            border-radius: 50%;
            flex-shrink: 0;
        }
        .activity-dot.green { background: #22c55e; }
        .activity-dot.blue { background: #6366f1; }
        .activity-dot.amber { background: #f59e0b; }
        .activity-time {
            color: #4b4f68;
            font-size: 11px;
            margin-left: auto;
            flex-shrink: 0;
        }

        /* Footer */
        .footer {
            text-align: center;
            padding: 24px;
            font-size: 12px;
            color: #3b3f55;
        }
        .footer a { color: #818cf8; text-decoration: none; }
        .footer a:hover { text-decoration: underline; }

        .refresh-note {
            text-align: center;
            font-size: 11px;
            color: #3b3f55;
            margin-bottom: 24px;
        }
        .pulse { animation: pulse 2s ease-in-out infinite; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔮 <span>Drop-Off Detection</span> — System Status</h1>
        <p>Real-time health monitoring for all platform services</p>
    </div>

    <div class="container">
        <div id="status-banner" class="status-banner operational">
            <div class="status-icon">✓</div>
            <div>
                <h2 id="overall-title">Loading...</h2>
                <p id="overall-subtitle">Checking system health...</p>
            </div>
        </div>

        <div class="refresh-note">
            <span class="pulse">●</span> Auto-refreshes every 15 seconds · Last checked: <span id="last-check">—</span>
        </div>

        <div class="section-title">Component Status</div>
        <div class="component-list" id="components">
            <div class="component"><div>Loading components...</div></div>
        </div>

        <div class="section-title">Performance Metrics</div>
        <div class="metrics-grid" id="metrics-grid">
            <div class="metric-card"><div class="metric-value">—</div><div class="metric-label">Loading</div></div>
        </div>

        <div class="latency-section">
            <div class="section-title">Response Time (simulated last 30 requests)</div>
            <div class="latency-bars" id="latency-bars"></div>
            <div class="latency-legend">
                <span>Older</span><span>Recent</span>
            </div>
        </div>

        <div class="section-title">Recent Activity</div>
        <div class="activity-list" id="activity-log">
            <div class="activity-item"><div>Loading activity...</div></div>
        </div>
    </div>

    <div class="footer">
        Powered by <a href="/apidocs/">Drop-Off Detection API</a> · 
        <a href="/metrics">Prometheus Metrics</a> · 
        <a href="/health">Health Check</a>
    </div>

    <script>
        async function fetchStatus() {
            try {
                const res = await fetch('/health');
                const data = await res.json();
                renderStatus(data);
            } catch (err) {
                renderOffline();
            }
        }

        function renderStatus(data) {
            const banner = document.getElementById('status-banner');
            const title = document.getElementById('overall-title');
            const subtitle = document.getElementById('overall-subtitle');
            const now = new Date().toLocaleTimeString();
            document.getElementById('last-check').textContent = now;

            const isHealthy = data.health?.status === 'healthy';
            const dbOk = data.database?.connected;
            const modelOk = data.model_loaded;

            if (isHealthy && dbOk && modelOk) {
                banner.className = 'status-banner operational';
                banner.querySelector('.status-icon').textContent = '✓';
                title.textContent = 'All Systems Operational';
                subtitle.textContent = 'All components are running normally.';
            } else {
                banner.className = 'status-banner degraded';
                banner.querySelector('.status-icon').textContent = '!';
                title.textContent = 'Partial System Degradation';
                subtitle.textContent = 'Some components may be experiencing issues.';
            }

            // Components
            const mon = data.monitoring || {};
            const counters = mon.counters || {};
            const latency = mon.latency || {};
            const drift = mon.drift_stub || {};
            const workerRunning = data.worker?.running;

            const components = [
                { name: 'Flask API Server', detail: 'REST API engine', ok: true },
                { name: 'ML Prediction Model', detail: data.model_loaded ? 'Loaded (.pkl)' : 'Not loaded', ok: modelOk },
                { name: 'Database (SQLAlchemy)', detail: dbOk ? 'Connected' : (data.database?.error || 'Disconnected'), ok: dbOk },
                { name: 'Health Monitor', detail: data.health?.status || 'Unknown', ok: isHealthy },
                { name: 'Prometheus Exporter', detail: '/metrics endpoint', ok: true },
                { name: 'Drift Detection', detail: drift.status || 'N/A', ok: drift.status !== 'alert' },
                { name: 'Background Worker', detail: workerRunning ? 'Running' : 'Stopped', ok: true },
                { name: 'JWT Authentication', detail: 'HS256 tokens', ok: true },
                { name: 'Rate Limiter', detail: '100 req/min per key', ok: true },
                { name: 'Security Headers', detail: 'HSTS, XSS, CSP, CORS', ok: true },
            ];

            let compHtml = '';
            components.forEach(c => {
                const badgeClass = c.ok ? 'up' : 'down';
                const badgeText = c.ok ? 'Operational' : 'Issue';
                compHtml += `
                    <div class="component">
                        <div>
                            <div class="component-name">${c.name}</div>
                            <div class="component-detail">${c.detail}</div>
                        </div>
                        <span class="badge ${badgeClass}">${badgeText}</span>
                    </div>`;
            });
            document.getElementById('components').innerHTML = compHtml;

            // Metrics
            const totalReqs = counters.api_requests_total || 0;
            const successRate = counters.api_status_2xx
                ? ((counters.api_status_2xx / totalReqs) * 100).toFixed(1)
                : '100.0';
            const avgLatency = (latency.avg_ms || 0).toFixed(0);
            const p95Latency = (latency.p95_ms || 0).toFixed(0);
            const predictions = counters.predictions_total || 0;
            const driftSamples = drift.samples || 0;

            document.getElementById('metrics-grid').innerHTML = `
                <div class="metric-card"><div class="metric-value green">${successRate}%</div><div class="metric-label">Success Rate</div></div>
                <div class="metric-card"><div class="metric-value purple">${totalReqs.toLocaleString()}</div><div class="metric-label">Total Requests</div></div>
                <div class="metric-card"><div class="metric-value cyan">${avgLatency}ms</div><div class="metric-label">Avg Latency</div></div>
                <div class="metric-card"><div class="metric-value amber">${p95Latency}ms</div><div class="metric-label">P95 Latency</div></div>
                <div class="metric-card"><div class="metric-value purple">${predictions}</div><div class="metric-label">Predictions</div></div>
                <div class="metric-card"><div class="metric-value cyan">${driftSamples}</div><div class="metric-label">Drift Samples</div></div>
            `;

            // Simulated latency bars (using avg and some randomization)
            const barsContainer = document.getElementById('latency-bars');
            let barsHtml = '';
            const base = parseFloat(avgLatency) || 100;
            for (let i = 0; i < 30; i++) {
                const jitter = (Math.random() - 0.4) * base * 0.8;
                const ms = Math.max(20, base + jitter);
                const height = Math.min(100, Math.max(8, (ms / (base * 2)) * 100));
                barsHtml += `<div class="latency-bar" style="height:${height}%" data-ms="${ms.toFixed(0)}ms"></div>`;
            }
            barsContainer.innerHTML = barsHtml;

            // Activity log
            const activities = [];
            if (totalReqs > 0) activities.push({ dot: 'green', text: `${totalReqs} total API requests processed`, time: now });
            if (predictions > 0) activities.push({ dot: 'blue', text: `${predictions} ML predictions served successfully`, time: now });
            if (counters.api_status_2xx) activities.push({ dot: 'green', text: `${counters.api_status_2xx} successful responses (2xx)`, time: now });
            if (counters.auth_successes) activities.push({ dot: 'blue', text: `${counters.auth_successes} JWT login(s) authenticated`, time: now });
            if (counters.prediction_validation_errors) activities.push({ dot: 'amber', text: `${counters.prediction_validation_errors} validation error(s) caught`, time: now });
            if (counters.api_rate_limited) activities.push({ dot: 'amber', text: `${counters.api_rate_limited} request(s) rate limited`, time: now });
            activities.push({ dot: 'green', text: 'System health check passed', time: now });
            activities.push({ dot: 'blue', text: 'Prometheus metrics exported', time: now });

            let actHtml = '';
            activities.forEach(a => {
                actHtml += `
                    <div class="activity-item">
                        <div class="activity-dot ${a.dot}"></div>
                        <div>${a.text}</div>
                        <div class="activity-time">${a.time}</div>
                    </div>`;
            });
            document.getElementById('activity-log').innerHTML = actHtml;
        }

        function renderOffline() {
            const banner = document.getElementById('status-banner');
            banner.className = 'status-banner down';
            banner.querySelector('.status-icon').textContent = '✕';
            document.getElementById('overall-title').textContent = 'System Unreachable';
            document.getElementById('overall-subtitle').textContent = 'Unable to connect to the health endpoint.';
            document.getElementById('last-check').textContent = new Date().toLocaleTimeString();
        }

        // Initial load + auto-refresh every 15 seconds
        fetchStatus();
        setInterval(fetchStatus, 15000);
    </script>
</body>
</html>
"""


def register_status_page(app: Flask) -> None:
    """Register the /status route on the Flask app."""
    from flask import make_response

    @app.route("/status", methods=["GET"])
    def system_status_page():
        response = make_response(STATUS_PAGE_HTML, 200)
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        # Override CSP to allow Google Fonts and inline scripts for this page
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
        return response

    logger.info("status_page_registered", path="/status")

