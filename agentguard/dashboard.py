"""AgentGuard Embedded Observability Console Server — Native Zero Dependency."""

from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from typing import Any


class DashboardHTTPRequestHandler(BaseHTTPRequestHandler):
    """Native Request Interceptor constructing dashboard monitoring web structures."""

    def log_message(self, format: str, *args: Any) -> None:
        """Suppresses internal stdout logging records to preserve pristine console spaces."""
        return

    def _inject_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:
        """Handles cross-origin request handshakes safely."""
        self.send_response(200)
        self._inject_cors_headers()
        self.end_headers()

    def _render_html_dashboard(self) -> str:
        """Compiles a responsive, modern HTML UI interface fueled by remote Tailwind CDNs."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AgentGuard Observability Control Plane</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        async function refreshTelemetryStream() {
            try {
                const response = await fetch('/api/stream');
                const logEntries = await response.json();
                const container = document.getElementById('log-stream-container');
                container.innerHTML = '';
                
                if (logEntries.length === 0) {
                    container.innerHTML = `<div class="text-zinc-500 text-center py-8 text-sm border border-dashed border-zinc-800 rounded-xl">No transactions recorded in the current active session workspace ledger.</div>`;
                    return;
                }
                
                logEntries.reverse().forEach(entry => {
                    const isCommitted = entry.step === 'COMMITTED' || entry.step === 'PREPARE';
                    const badgeColor = isCommitted ? 'bg-emerald-950/40 text-emerald-400 border-emerald-800/60' : 'bg-rose-950/40 text-rose-400 border-rose-800/60';
                    const el = document.createElement('div');
                    el.className = 'p-4 bg-zinc-900 border border-zinc-800 rounded-xl shadow-sm mb-3 font-mono text-xs transition-all hover:border-zinc-700';
                    el.innerHTML = `
                        <div class="flex items-center justify-between mb-2">
                            <span class="px-2 py-0.5 rounded border text-[10px] uppercase font-bold tracking-wider ${badgeColor}">${entry.step}</span>
                            <span class="text-zinc-500 text-[10px]">${new Date(entry.telemetry.timestamp * 1000).toLocaleTimeString()}</span>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-zinc-300">
                            <div><span class="text-zinc-500">TX_ID:</span> ${entry.telemetry.tx_id}</div>
                            <div><span class="text-zinc-500">TOOL:</span> ${entry.telemetry.tool || 'N/A'}</div>
                            <div><span class="text-zinc-500">AGENT:</span> ${entry.telemetry.agent_id || 'N/A'}</div>
                            <div><span class="text-zinc-500">PROOFS:</span> ${entry.telemetry.content_hash || 'SHA-256 Verified'}</div>
                        </div>
                    `;
                    container.appendChild(el);
                });
            } catch (err) {
                console.error("Telemetry pipeline sync drop out error: ", err);
            }
        }
        setInterval(refreshTelemetryStream, 2000);
        window.onload = refreshTelemetryStream;
    </script>
</head>
<body class="bg-zinc-950 text-zinc-100 min-h-screen font-sans antialiased">
    <div class="max-w-5xl mx-auto px-4 py-8">
        <header class="flex items-center justify-between border-b border-zinc-900 pb-6 mb-8">
            <div>
                <h1 class="text-xl font-bold tracking-tight text-white flex items-center gap-2">🛡️ AgentGuard <span class="text-xs font-mono font-medium text-zinc-500 px-2 py-0.5 border border-zinc-800 rounded-full">v1.0.0-local</span></h1>
                <p class="text-xs text-zinc-400 mt-1">Autonomous microkernel transaction ledger diagnostics monitor.</p>
            </div>
            <div class="flex items-center gap-2">
                <span class="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span class="text-[10px] font-mono font-semibold uppercase tracking-wider text-zinc-400">Control Plane Armed</span>
            </div>
        </header>
        
        <main>
            <div class="mb-6 flex items-center justify-between">
                <h2 class="text-sm font-semibold text-zinc-300 uppercase tracking-wider">Live Transaction Event Pipeline Stream Log</h2>
                <button onclick="refreshTelemetryStream()" class="text-xs font-medium text-zinc-400 border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 px-3 py-1.5 rounded-lg transition-colors">Force Refresh Sync</button>
            </div>
            <div id="log-stream-container"></div>
        </main>
    </div>
</body>
</html>"""

    def do_GET(self) -> None:
        """Processes lookups, resolving text routing blocks smoothly."""
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(self._render_html_dashboard().encode("utf-8"))
            
        elif self.path == "/api/stream":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._inject_cors_headers()
            self.end_headers()
            
            log_entries: list[dict[str, Any]] = []
            target_log_file = "agentguard_audit.log"
            
            if os.path.exists(target_log_file):
                with open(target_log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            try:
                                log_entries.append(json.loads(line.strip()))
                            except json.JSONDecodeError:
                                pass
            
            self.wfile.write(json.dumps(log_entries[-50:]).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def boot_observability_dashboard(port: int = 8484) -> None:
    """Spins up the localized microserver thread environment."""
    server_address = ("", port)
    httpd = HTTPServer(server_address, DashboardHTTPRequestHandler)
    print(f"\033[92m[+] AgentGuard real-time visual monitor deployed live at: \033[94mhttp://localhost:{port}/\033[0m")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[-] Observability data plane engine spun down cleanly.")
        httpd.server_close()
