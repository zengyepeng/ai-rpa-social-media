#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
影刀 ↔ 云电脑AI服务 中转桥
在本地笔记本运行，影刀调这个，它转发到云电脑
"""

import json
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# ===== 改成你的云电脑IP =====
CLOUD_IP = "43.140.208.144"
CLOUD_PORT = 8888

def forward(path, body=None):
    """转发请求到云电脑"""
    url = f"http://{CLOUD_IP}:{CLOUD_PORT}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"code": -1, "message": str(e)}

class BridgeHandler(BaseHTTPRequestHandler):
    def _send(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

        if path in ["/agent/generate", "/agent/reply", "/agent/analyze", "/agent/ping"]:
            result = forward(path, body)
            self._send(200, result)
        else:
            self._send(404, {"code": -1, "message": "not found"})

    def do_GET(self):
        self.do_POST()

    def log_message(self, fmt, *args):
        print(f"[Bridge] {args[0]} {args[1]} {args[2]}")

print("=" * 50)
print("影刀 ↔ 云电脑 中转桥")
print("=" * 50)
print(f"云电脑地址: http://{CLOUD_IP}:{CLOUD_PORT}")
print(f"本地地址:   http://127.0.0.1:8888")
print()
print("影刀里填: http://127.0.0.1:8888/agent/generate")
print()
print("启动中...")

server = HTTPServer(("0.0.0.0", 8888), BridgeHandler)
print("✅ 已启动！按 Ctrl+C 停止")
server.serve_forever()
