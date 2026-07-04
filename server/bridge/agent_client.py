#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小叶的本地Agent客户端 v3.0 - 轮询版
每5秒问我有没有指令，有就执行，不需要WebSocket
"""

import json
import time
import subprocess
import webbrowser
import socket
import urllib.request
import urllib.error

# ===== 配置 =====
SERVER_URL = "http://43.140.208.144:8889"

# ===== 桌面控制模块 =====
try:
    import pyautogui
    HAS_PYAUTOGUI = True
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.3
except ImportError:
    HAS_PYAUTOGUI = False


def handle_action(action, params):
    """执行指令"""
    
    if action == "mouse_move":
        pyautogui.moveTo(params["x"], params["y"], duration=0.3)
        return {"code": 0}
    
    elif action == "mouse_click":
        x, y = params.get("x"), params.get("y")
        btn = params.get("button", "left")
        pyautogui.click(x, y, button=btn) if x else pyautogui.click(button=btn)
        return {"code": 0}
    
    elif action == "mouse_doubleclick":
        pyautogui.doubleClick(params.get("x"), params.get("y"))
        return {"code": 0}
    
    elif action == "mouse_position":
        x, y = pyautogui.position()
        return {"code": 0, "data": {"x": x, "y": y}}
    
    elif action == "mouse_scroll":
        pyautogui.scroll(params.get("clicks", 1))
        return {"code": 0}
    
    elif action == "keyboard_type":
        pyautogui.write(params.get("text", ""), interval=0.05)
        return {"code": 0}
    
    elif action == "keyboard_press":
        pyautogui.press(params.get("key", ""))
        return {"code": 0}
    
    elif action == "keyboard_hotkey":
        pyautogui.hotkey(*params.get("keys", []))
        return {"code": 0}
    
    elif action == "screen_screenshot":
        filename = params.get("filename", f"screenshot_{int(time.time())}.png")
        pyautogui.screenshot(filename)
        return {"code": 0, "file": filename}
    
    elif action == "screen_size":
        w, h = pyautogui.size()
        return {"code": 0, "data": {"width": w, "height": h}}
    
    elif action == "system_command":
        r = subprocess.run(params.get("cmd", ""), shell=True, capture_output=True, text=True, timeout=30)
        return {"code": 0, "stdout": r.stdout[-1000:], "stderr": r.stderr[-1000:]}
    
    elif action == "browser_open":
        webbrowser.open(params.get("url", ""))
        return {"code": 0}
    
    elif action == "ping":
        return {"code": 0, "message": "pong", "has_pyautogui": HAS_PYAUTOGUI}
    
    else:
        return {"code": -1, "message": f"未知指令: {action}"}


def main():
    print("=" * 50)
    print("  小叶的本地Agent客户端 v3.0")
    print("=" * 50)
    print(f"  PyAutoGUI: {'✅' if HAS_PYAUTOGUI else '❌'}")
    print(f"  云服务器: {SERVER_URL}")
    print()
    
    if not HAS_PYAUTOGUI:
        print("❌ PyAutoGUI 未安装，运行: pip install pyautogui pillow")
        print()
        return
    
    print("  正在连接...")
    print()
    
    # 先ping一下看云服务器通不通
    try:
        req = urllib.request.Request(f"{SERVER_URL}/ping")
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode("utf-8"))
        if result.get("code") == 0:
            print(f"  ✅ 云服务器连接正常!")
            print(f"  💡 等待指令中...")
            print()
        else:
            print(f"  ⚠️ 云服务器响应异常: {result}")
    except Exception as e:
        print(f"  ❌ 连不上云服务器: {e}")
        print(f"  检查网络或云服务器是否在运行")
        print()
        return
    
    # 报告在线
    try:
        data = json.dumps({
            "status": "online",
            "hostname": socket.gethostname(),
            "has_pyautogui": HAS_PYAUTOGUI,
            "screen_size": list(pyautogui.size())
        }).encode("utf-8")
        req = urllib.request.Request(f"{SERVER_URL}/agent/register", data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
        print("  ✅ 已向云服务器注册")
        print()
    except:
        print("  ⚠️ 注册失败，但轮询仍会继续")
    
    print("  ========== 等待小叶指令 ==========")
    print()
    
    cmd_id = 0
    while True:
        try:
            cmd_id += 1
            # 问我：有没有活干？
            data = json.dumps({"cmd_id": cmd_id}).encode("utf-8")
            req = urllib.request.Request(
                f"{SERVER_URL}/agent/poll", 
                data=data,
                headers={"Content-Type": "application/json"}
            )
            resp = urllib.request.urlopen(req, timeout=10)
            result = json.loads(resp.read().decode("utf-8"))
            
            # 有指令就执行
            if result.get("code") == 0 and result.get("action"):
                action = result["action"]
                params = result.get("params", {})
                
                action_names = {
                    "mouse_move": "🖱️ 移动鼠标", "mouse_click": "🖱️ 点击",
                    "keyboard_type": "⌨️ 输入文字", "keyboard_hotkey": "⌨️ 快捷键",
                    "screen_screenshot": "📸 截图", "system_command": "⚡ 命令",
                    "browser_open": "🌐 打开网页",
                }
                name = action_names.get(action, f"🔧 {action}")
                print(f"  收到指令: {name}")
                
                try:
                    result = handle_action(action, params)
                    result["cmd_id"] = cmd_id
                    # 汇报执行结果
                    req2 = urllib.request.Request(
                        f"{SERVER_URL}/agent/result",
                        data=json.dumps(result).encode("utf-8"),
                        headers={"Content-Type": "application/json"}
                    )
                    urllib.request.urlopen(req2, timeout=5)
                    print(f"  {'✅' if result.get('code') == 0 else '❌'} 执行完成")
                except Exception as e:
                    print(f"  ❌ 执行失败: {e}")
                    urllib.request.urlopen(
                        f"{SERVER_URL}/agent/result",
                        data=json.dumps({"cmd_id": cmd_id, "code": -1, "message": str(e)}).encode("utf-8"),
                        headers={"Content-Type": "application/json"}
                    )
            
        except Exception:
            pass  # 没指令就继续等
        
        time.sleep(3)  # 每3秒问一次


if __name__ == "__main__":
    main()
