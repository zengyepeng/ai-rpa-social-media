# 通信API设计

## 概述

AI Agent（服务器）与影刀RPA（本地）通过HTTP进行双向通信。

## Agent → 影刀指令

### 1. 发布内容

```
POST /rpa/post
Content-Type: application/json

{
  "task_id": "post_20260702_001",
  "type": "post",
  "params": {
    "platform": "xiaohongshu",
    "title": "标题内容",
    "content": "正文内容...",
    "images": ["url1", "url2"],
    "tags": ["标签1", "标签2"],
    "schedule_time": "2026-07-02 20:00:00"
  }
}
```

### 2. 回复评论

```
POST /rpa/reply
{
  "task_id": "reply_20260702_001",
  "type": "reply",
  "params": {
    "platform": "xiaohongshu",
    "note_url": "...",
    "comment_id": "...",
    "reply_content": "回复内容..."
  }
}
```

### 3. 获取数据

```
POST /rpa/fetch_data
{
  "task_id": "data_20260702_001",
  "type": "fetch_data",
  "params": {
    "platform": "xiaohongshu",
    "data_type": "account_stats"  // 账号概览数据
  }
}
```

## 影刀 → Agent 回执

### 成功回调
```
POST /webhook/task_result
{
  "task_id": "post_20260702_001",
  "status": "success",
  "result": {
    "note_url": "https://xiaohongshu.com/...",
    "publish_time": "2026-07-02 20:01:30"
  }
}
```

### 失败回调
```
POST /webhook/task_result
{
  "task_id": "post_20260702_001",
  "status": "failed",
  "error": {
    "code": "LOGIN_EXPIRED",
    "message": "登录已失效，需要重新登录"
  }
}
```
