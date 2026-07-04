#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云服务器指挥端 v3.0 - 轮询版
老板笔记本每3秒来问有没有指令
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

PORT = 8889

# 本地Agent状态
agent_online = False
agent_info = {}

# 指令队列
command_queue = {}      # cmd_id -> 待执行的指令
result_queue = {}       # cmd_id -> 执行结果
last_cmd_id = 0
agent_cmd_id = 0


class CommanderHandler(BaseHTTPRequestHandler):
    def _send(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_POST(self):
        global agent_online, agent_info, last_cmd_id, agent_cmd_id
        
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

        # 本地Agent注册
        if path == "/agent/register":
            agent_online = True
            agent_info = body
            print(f"\n[💚] 老板笔记本上线！")
            print(f"  主机: {body.get('hostname', '?')}")
            print(f"  屏幕: {body.get('screen_size', '?')}")
            print(f"  PyAutoGUI: {'✅' if body.get('has_pyautogui') else '❌'}")
            print()
            self._send(200, {"code": 0, "message": "registered"})

        # 本地Agent轮询指令
        elif path == "/agent/poll":
            if command_queue:
                cid = list(command_queue.keys())[0]
                cmd = command_queue.pop(cid)
                agent_cmd_id = cid
                self._send(200, {"code": 0, "action": cmd["action"], "params": cmd["params"]})
            else:
                self._send(200, {"code": 0})  # 没指令

        # 本地Agent汇报执行结果
        elif path == "/agent/result":
            result_queue[body.get("cmd_id", 0)] = body
            self._send(200, {"code": 0})

        # 健康检查
        elif path == "/ping":
            self._send(200, {
                "code": 0, 
                "message": "pong",
                "agent_online": agent_online,
                "agent_info": agent_info if agent_online else {}
            })

        # 状态
        elif path == "/status":
            self._send(200, {
                "code": 0,
                "data": {
                    "agent_online": agent_online,
                    "agent_info": agent_info,
                    "pending_commands": len(command_queue),
                    "last_result": result_queue.get(agent_cmd_id) if agent_cmd_id else None
                }
            })

        # 我来发指令给老板的电脑
        elif path.startswith("/cmd/"):
            action = path.replace("/cmd/", "")
            last_cmd_id += 1
            command_queue[last_cmd_id] = {"action": action, "params": body}
            print(f"[📤] 发送指令: {action}")
            self._send(200, {"code": 0, "cmd_id": last_cmd_id, "message": "指令已发送"})

        else:
            self._send(404, {"code": -1, "message": "not found"})

    def do_GET(self):
        self.do_POST()

    def log_message(self, fmt, *args):
        pass


def main():
    server = HTTPServer(("0.0.0.0", PORT), CommanderHandler)
    print("=" * 50)
    print("  小叶指挥端 v3.0 - 轮询版")
    print("=" * 50)
    print(f"  监听端口: {PORT}")
    print(f"  等待老板笔记本连接...")
    print()
    server.serve_forever()


if __name__ == "__main__":
    main()
