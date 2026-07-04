#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模块 - SQLite
存储账号数据、内容记录、发布历史、任务日志
"""

import sqlite3
import json
import os
from datetime import datetime

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "social_media.db")


def get_conn():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化所有表"""
    conn = get_conn()
    cur = conn.cursor()

    # 1. 账号表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,              -- xiaohongshu / douyin / weibo
            username TEXT NOT NULL,
            nickname TEXT DEFAULT '',
            status TEXT DEFAULT 'active',        -- active / expired / banned
            cookie TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(platform, username)
        )
    """)

    # 2. 内容发布记录
    cur.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE,
            account_id INTEGER,
            platform TEXT NOT NULL,
            title TEXT,
            content TEXT,
            images TEXT DEFAULT '[]',            -- JSON array of URLs
            tags TEXT DEFAULT '[]',              -- JSON array of tags
            style TEXT DEFAULT '种草',
            status TEXT DEFAULT 'pending',       -- pending / published / failed
            note_url TEXT DEFAULT '',
            publish_time TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    """)

    # 3. 评论回复记录
    cur.execute("""
        CREATE TABLE IF NOT EXISTS replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE,
            account_id INTEGER,
            platform TEXT NOT NULL,
            note_url TEXT,
            comment_id TEXT,
            original_comment TEXT,
            reply_content TEXT,
            status TEXT DEFAULT 'pending',       -- pending / replied / failed
            replied_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    """)

    # 4. 账号数据快照（阅读、点赞、涨粉等）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stats_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER,
            platform TEXT NOT NULL,
            followers INTEGER DEFAULT 0,
            following INTEGER DEFAULT 0,
            total_notes INTEGER DEFAULT 0,
            total_likes INTEGER DEFAULT 0,
            total_collects INTEGER DEFAULT 0,
            snapshot_date DATE DEFAULT (date('now', '+08:00', 'start of day')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    """)

    # 5. 任务日志（统一任务流水）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS task_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE,
            task_type TEXT NOT NULL,             -- post / reply / fetch_data / login
            platform TEXT,
            status TEXT DEFAULT 'pending',       -- pending / running / success / failed
            request_body TEXT,                   -- JSON
            response_body TEXT,                  -- JSON
            error_msg TEXT,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)

    # 6. 内容模板库
    cur.execute("""
        CREATE TABLE IF NOT EXISTS content_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            style TEXT DEFAULT '种草',
            system_prompt TEXT,
            user_prompt_template TEXT,
            tags TEXT DEFAULT '[]',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print(f"[DB] 数据库初始化完成: {DB_PATH}")


# ========== 账号操作 ==========

def add_account(platform, username, nickname="", cookie=""):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO accounts (platform, username, nickname, cookie) VALUES (?, ?, ?, ?)",
            (platform, username, nickname, cookie)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] add_account error: {e}")
        return False
    finally:
        conn.close()


def get_accounts(platform=None):
    conn = get_conn()
    if platform:
        rows = conn.execute("SELECT * FROM accounts WHERE platform = ? ORDER BY id", (platform,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM accounts ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ========== 内容发布操作 ==========

def save_post(task_id, platform, title="", content="", images=None, tags=None, style="种草"):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO posts (task_id, platform, title, content, images, tags, style) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (task_id, platform, title, content, json.dumps(images or [], ensure_ascii=False),
             json.dumps(tags or [], ensure_ascii=False), style)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] save_post error: {e}")
        return False
    finally:
        conn.close()


def update_post_status(task_id, status, note_url=""):
    conn = get_conn()
    conn.execute(
        "UPDATE posts SET status=?, note_url=?, updated_at=CURRENT_TIMESTAMP WHERE task_id=?",
        (status, note_url, task_id)
    )
    conn.commit()
    conn.close()


def get_pending_posts():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM posts WHERE status='pending' ORDER BY created_at").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ========== 任务日志操作 ==========

def log_task(task_id, task_type, platform="", request_body=None):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO task_log (task_id, task_type, platform, request_body) VALUES (?, ?, ?, ?)",
            (task_id, task_type, platform, json.dumps(request_body or {}, ensure_ascii=False))
        )
        conn.commit()
    except Exception as e:
        print(f"[DB] log_task error: {e}")
    finally:
        conn.close()


def update_task_status(task_id, status, response_body=None, error_msg=""):
    conn = get_conn()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status in ("success", "failed") else None
    conn.execute(
        "UPDATE task_log SET status=?, response_body=?, error_msg=?, completed_at=? WHERE task_id=?",
        (status, json.dumps(response_body or {}, ensure_ascii=False) if response_body else None,
         error_msg, now, task_id)
    )
    conn.commit()
    conn.close()


def get_recent_tasks(limit=20):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM task_log ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ========== 内容模板操作 ==========

def add_template(name, style, system_prompt, user_prompt_template, tags=None):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO content_templates (name, style, system_prompt, user_prompt_template, tags) VALUES (?, ?, ?, ?, ?)",
            (name, style, system_prompt, user_prompt_template, json.dumps(tags or [], ensure_ascii=False))
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] add_template error: {e}")
        return False
    finally:
        conn.close()


def get_templates(style=None):
    conn = get_conn()
    if style:
        rows = conn.execute("SELECT * FROM content_templates WHERE style=? AND is_active=1 ORDER BY id", (style,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM content_templates WHERE is_active=1 ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ========== 数据快照 ==========

def save_snapshot(account_id, platform, followers=0, following=0, total_notes=0, total_likes=0, total_collects=0):
    conn = get_conn()
    conn.execute(
        "INSERT INTO stats_snapshots (account_id, platform, followers, following, total_notes, total_likes, total_collects) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (account_id, platform, followers, following, total_notes, total_likes, total_collects)
    )
    conn.commit()
    conn.close()


def get_latest_snapshot(account_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM stats_snapshots WHERE account_id=? ORDER BY snapshot_date DESC LIMIT 1",
        (account_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


if __name__ == "__main__":
    init_db()
    print("[DB] 数据库测试通过")
