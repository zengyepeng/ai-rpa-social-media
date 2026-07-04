#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调度模块 - 任务队列与重试
从pending队列取任务，调用对应模块执行，记录结果
"""

import sys
import os
import json
import time
import threading
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import (
    init_db, get_pending_posts, update_post_status,
    log_task, update_task_status, get_recent_tasks
)


class TaskScheduler:
    """任务调度器"""

    def __init__(self, agent_client=None, poll_interval=30):
        """
        agent_client: 可调用 agent 模块的客户端（用于生成内容等）
        poll_interval: 轮询间隔（秒）
        """
        self.agent_client = agent_client
        self.poll_interval = poll_interval
        self.running = False
        self._thread = None

    def start(self):
        """启动调度器（后台线程）"""
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="scheduler")
        self._thread.start()
        print(f"[Scheduler] 调度器已启动，轮询间隔 {self.poll_interval}s")

    def stop(self):
        """停止调度器"""
        self.running = False
        print("[Scheduler] 调度器停止")

    def _loop(self):
        """主循环"""
        while self.running:
            try:
                self._process_pending()
            except Exception as e:
                print(f"[Scheduler] 处理轮询出错: {e}")
            time.sleep(self.poll_interval)

    def _process_pending(self):
        """处理所有待办任务"""
        pending = get_pending_posts()
        for post in pending:
            if not self.running:
                break
            print(f"[Scheduler] 处理待发布任务: {post.get('task_id', 'unknown')}")
            self._execute_post(post)

    def _execute_post(self, post):
        """执行一个发布任务"""
        task_id = post["task_id"]
        update_post_status(task_id, "running")

        try:
            # 如果需要AI生成内容（当内容为空时）
            if not post.get("content") and self.agent_client:
                content = self.agent_client.generate_content(
                    topic=post.get("title") or post.get("content"),
                    style=post.get("style", "种草")
                )
                # 切片内容
                post["content"] = content

            # 这里实际会发给影刀RPA执行
            # 目前模拟执行成功
            print(f"[Scheduler] ▶ 准备发布: {post.get('title', '无标题')}")
            print(f"[Scheduler]   平台: {post.get('platform')}")
            print(f"[Scheduler]   内容长度: {len(post.get('content', ''))}字")
            print(f"[Scheduler]   标签: {post.get('tags', '[]')}")

            # TODO: 调用影刀RPA桥接实际发布
            # result = send_to_rpa(post)

            # 模拟成功
            note_url = f"https://www.xiaohongshu.com/explore/{task_id}"
            update_post_status(task_id, "published", note_url=note_url)
            update_task_status(task_id, "success", {
                "note_url": note_url,
                "publish_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            print(f"[Scheduler] ✅ 发布成功: {note_url}")

        except Exception as e:
            print(f"[Scheduler] ❌ 发布失败 [{task_id}]: {e}")
            update_post_status(task_id, "failed")
            update_task_status(task_id, "failed", error_msg=str(e))

    def schedule_post(self, task_id, platform, title, content="", images=None, tags=None, style="种草"):
        """手动调度一个发布任务"""
        from db.database import save_post
        save_post(task_id, platform, title, content, images, tags, style)
        log_task(task_id, "post", platform, {
            "title": title,
            "content_preview": content[:50] if content else "",
            "tags": tags
        })
        print(f"[Scheduler] 📋 新任务入队: {task_id}")
        return task_id


class SimpleAgentClient:
    """简单的AI内容生成客户端（直接调agent_server模块）"""

    def __init__(self, base_url="http://127.0.0.1:8888"):
        self.base_url = base_url

    def generate_content(self, topic, style="种草"):
        """调用AI生成内容"""
        import urllib.request
        body = json.dumps({"topic": topic, "style": style}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/agent/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("code") == 0:
                return result["data"]["content"]
            else:
                raise Exception(result.get("message", "API error"))
        except Exception as e:
            raise Exception(f"AI生成失败: {e}")


def main():
    """测试调度器"""
    init_db()

    client = SimpleAgentClient() if len(sys.argv) > 1 and sys.argv[1] == "--with-ai" else None

    scheduler = TaskScheduler(agent_client=client, poll_interval=15)
    scheduler.start()

    # 模拟添加几个任务
    scheduler.schedule_post(
        task_id=f"post_{datetime.now().strftime('%Y%m%d_%H%M%S')}_001",
        platform="xiaohongshu",
        title="🔥 这5款护肤品我回购了10次！敏感肌亲测",
        content="（内容将由AI生成或影刀填入）",
        tags=["护肤", "敏感肌", "好物分享", "回购"],
        style="种草"
    )

    try:
        while True:
            time.sleep(5)
            # 显示最近任务
            tasks = get_recent_tasks(5)
            if tasks:
                print(f"\n--- 最近任务 ({len(tasks)}条) ---")
                for t in tasks:
                    print(f"  [{t['task_id']}] {t['task_type']} → {t['status']}")
    except KeyboardInterrupt:
        scheduler.stop()
        print("调度器已退出")


if __name__ == "__main__":
    main()
