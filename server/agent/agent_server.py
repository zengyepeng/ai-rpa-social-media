#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Agent Service
"""

import json, os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from openai import OpenAI

PORT = int(os.environ.get("AGENT_PORT", "8888"))

def load_api_key():
    paths = ["/tmp/deepseek_key_clean.txt", "/root/.openclaw/workspace/.deepseek_key"]
    for p in paths:
        try:
            with open(p) as f:
                k = f.read().strip()
                if k:
                    return k
        except:
            pass
    try:
        with open("/root/.openclaw/openclaw.json.bak.3") as f:
            cfg = json.load(f)
        for v in cfg.get("models", {}).get("providers", {}).values():
            if isinstance(v, dict) and "apiKey" in v:
                k = str(v["apiKey"])
                clean = "".join(c for c in k if ord(c) < 128)
                if clean.startswith("sk-"):
                    return clean
    except:
        pass
    return os.environ.get("DEEPSEEK_API_KEY", "")

API_KEY = load_api_key()
client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com/v1") if API_KEY else None

SYSTEM_PROMPT = "你是小红书运营专家，擅长写爆款文案。"
SYSTEM_REPLY = "你是小红书的博主，回复粉丝评论语气要亲切自然。"
SYSTEM_ANALYZE = "你是社交媒体数据分析师。"

def generate_post(topic=None, style="种草"):
    if not client:
        return "AI not configured"
    t = topic if topic else "自由发挥一个近期热门话题"
    prompt = f"你是一个小红书爆款文案写手。风格：{style}。写一篇吸引人的小红书笔记。标题要带数字和emoji，正文口语化有个人体验感，加3-5个标签，300字以内。选题：{t}"
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        temperature=0.8, max_tokens=800
    )
    return resp.choices[0].message.content

def generate_reply(comment_text):
    if not client:
        return "AI not configured"
    prompt = f"用户评论：{comment_text}。请生成一个自然友好的回复（20字以内），不要像机器人："
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": SYSTEM_REPLY}, {"role": "user", "content": prompt}],
        temperature=0.7, max_tokens=200
    )
    return resp.choices[0].message.content

def analyze_trending(topics_data):
    if not client:
        return "AI not configured"
    data_str = json.dumps(topics_data, ensure_ascii=False)
    prompt = f"分析这些热门话题数据：{data_str}。1.哪些有持续热度 2.下一步做什么选题 3.给出3个具体选题方向"
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": SYSTEM_ANALYZE}, {"role": "user", "content": prompt}],
        temperature=0.5, max_tokens=600
    )
    return resp.choices[0].message.content

class AgentHandler(BaseHTTPRequestHandler):
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
        try:
            if path == "/agent/generate":
                self._send(200, {"code": 0, "data": {"content": generate_post(body.get("topic"), body.get("style", "种草"))}})
            elif path == "/agent/reply":
                self._send(200, {"code": 0, "data": {"reply": generate_reply(body.get("comment", ""))}})
            elif path == "/agent/analyze":
                self._send(200, {"code": 0, "data": {"advice": analyze_trending(body.get("topics", []))}})
            elif path == "/agent/ping":
                self._send(200, {"code": 0, "message": "pong", "api_ok": client is not None})
            else:
                self._send(404, {"code": -1, "message": "not found"})
        except Exception as e:
            self._send(500, {"code": -1, "message": str(e)})

    def do_GET(self):
        self.do_POST()

    def log_message(self, fmt, *args):
        print(f"[Agent] {args[0]} {args[1]} {args[2]}")

def main():
    if not API_KEY:
        print("WARNING: No API Key")
    server = HTTPServer(("0.0.0.0", PORT), AgentHandler)
    print(f"Agent running on http://0.0.0.0:{PORT}")
    print(f"  POST /agent/generate  /agent/reply  /agent/analyze  GET /agent/ping")
    print(f"  API Key: {bool(API_KEY)}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped")
        server.server_close()

if __name__ == "__main__":
    main()
