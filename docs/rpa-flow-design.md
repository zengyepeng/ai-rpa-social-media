# 影刀RPA流程设计文档

> AI Agent + 影刀RPA 社交媒体智能运营系统
> 版本: v1.0 | 日期: 2026-07-04

---

## 系统通信方式

```
影刀RPA ──HTTP──► 中转桥(bridge.py) ──HTTP──► AI Agent服务器
                                                  │
                                              SQLite数据库
```

**关键信息：**
- AI Agent服务器地址: 我这边跑着，你不需要关心
- 中转桥（bridge.py）: 在你本地电脑跑，影刀调它，它转发到我的服务器
- 如果影刀没有"HTTP请求"积木 → 用我写的Python脚本替代中转桥

---

## 流程总览

| 编号 | 流程名 | 说明 | 优先级 |
|------|--------|------|--------|
| 1 | 登录小红书 | 扫码/密码登录，保存Cookie | ⭐⭐⭐ |
| 2 | 发布图文笔记 | 打开创作中心→填内容→发 | ⭐⭐⭐ |
| 3 | 回复评论 | 查评论→AI生成回复→发 | ⭐⭐ |
| 4 | 采集账号数据 | 截取粉丝/点赞数→回传 | ⭐⭐ |

---

## 流程1：登录小红书

### 触发方式
- 手动启动
- 或 Agent检测到Cookie失效后通知

### 详细步骤

| 步骤 | 影刀操作 | 说明 |
|------|----------|------|
| 1.1 | 打开Chrome，访问 https://creator.xiaohongshu.com | 小红书创作平台 |
| 1.2 | 等待页面加载完成（等待元素"登录"按钮出现） | 最多等30秒 |
| 1.3 | 点击"登录"按钮 | - |
| 1.4 | 选择"手机号登录"或"扫码登录" | 推荐手机号+验证码 |
| 1.5 | 输入手机号，点击获取验证码 | - |
| 1.6 | 【暂停等待】手动输入验证码 | 影刀不能自动收短信 |
| 1.7 | 登录成功后，等待页面跳转到创作中心 | 检测到"创作中心"字样 |
| 1.8 | 通过Python脚本获取Cookie | 见下文代码 |
| 1.9 | 将Cookie发送到Agent服务器 | `POST /webhook/cookie` |

### 获取Cookie的Python脚本（给影刀的"运行Python"积木用）

```python
# 保存为 get_cookie.py，在影刀里调
import json

def get_chrome_cookie():
    """从当前Chrome获取小红书Cookie"""
    import browser_cookie3
    cookies = browser_cookie3.chrome(domain_name=".xiaohongshu.com")
    cookie_dict = {}
    for c in cookies:
        cookie_dict[c.name] = c.value
    return cookie_dict

cookie = get_chrome_cookie()
# 打印出来，影刀可以捕获输出
print(json.dumps(cookie))
```

---

## 流程2：发布图文笔记

### 触发方式
- 定时执行（比如每天10:00、16:00）
- 或 Agent服务器下发指令

### 详细步骤

| 步骤 | 影刀操作 | 说明 |
|------|----------|------|
| 2.0 | 【可选】先调API获取AI内容 | `POST /agent/generate` → 拿到标题+正文+标签 |
| 2.1 | 打开Chrome到创作中心 | https://creator.xiaohongshu.com |
| 2.2 | 点击"发布笔记"按钮 | 等待元素出现 |
| 2.3 | 选择"上传图文" | - |
| 2.4 | 点击上传区域，选择图片文件 | 图片路径事先准备好 |
| 2.5 | 等待图片上传完成 | 等待"图片上传成功"提示或进度条消失 |
| 2.6 | 在标题输入框填入标题 | 从AI生成结果取 |
| 2.7 | 在正文输入框填入内容 | 从AI生成结果取 |
| 2.8 | 点击"添加标签" | - |
| 2.9 | 填入标签（用逗号或空格分隔） | 从AI生成结果取 |
| 2.10 | 点击"发布"按钮 | - |
| 2.11 | 等待发布成功提示 | 检测"发布成功"字样 |
| 2.12 | 获取笔记链接 | 从页面URL或提示信息中提取 |
| 2.13 | 回传结果给Agent | `POST /webhook/task_result` |

### 影刀需要的配置参数

```
图片目录: D:\小红书图片\ (放好要发的图片)
发布时间: 从Agent获取 或 固定时间
是否立即发布: 是 / 定时发布
```

---

## 流程3：回复评论

### 触发方式
- 定时轮询（比如每2小时）
- 或 Agent服务器通知有新的待回复评论

### 详细步骤

| 步骤 | 影刀操作 |
|------|----------|
| 3.1 | 打开创作中心 → 消息 → 评论 |
| 3.2 | 遍历未回复的评论列表 |
| 3.3 | 对每条未回复评论： |
| 3.3.1 | 复制评论内容 |
| 3.3.2 | 调 `POST /agent/reply` 获取AI回复 |
| 3.3.3 | 在回复框填入AI回复内容 |
| 3.3.4 | 点击"发送"按钮 |
| 3.4 | 全部回复完成后，通知Agent |

---

## 流程4：采集账号数据

### 触发方式
- 每天一次定时执行

### 步骤

| 步骤 | 影刀操作 |
|------|----------|
| 4.1 | 打开创作中心 → 数据中心 |
| 4.2 | 截图或读取显示的：粉丝数、笔记数、获赞数 |
| 4.3 | 将数据发送到Agent | `POST /webhook/collect_data` |

---

## 影刀HTTP调用方法

### 方法A：影刀自带的"HTTP请求"积木

如果影刀有"发送HTTP请求"积木，直接填：

```
URL: http://127.0.0.1:8888/agent/generate
方法: POST
请求头: Content-Type: application/json
请求体: {"topic":"夏天防晒推荐","style":"种草"}
```

### 方法B：用Python脚本（推荐）

如果影刀没有HTTP请求积木，用"运行Python脚本"积木跑这个：

```python
# 保存为 call_agent.py
import json
import urllib.request

def call_agent(api_path, data):
    """调AI Agent接口"""
    url = f"http://127.0.0.1:8888{api_path}"
    req_data = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url, data=req_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read().decode("utf-8"))
    # 打印结果，影刀可以捕获
    print(json.dumps(result, ensure_ascii=False))
    return result

# 使用示例
result = call_agent("/agent/generate", {
    "topic": "夏天敏感肌防晒推荐",
    "style": "种草"
})
```

### 方法C：中转桥（bridge.py）

如果影刀不支持Python脚本，在我这边启动另一个服务做中转。

---

## API接口速查

| 接口 | 方法 | 参数 | 返回 |
|------|------|------|------|
| `/agent/generate` | POST | `{topic, style}` | `{content}` |
| `/agent/reply` | POST | `{comment}` | `{reply}` |
| `/agent/analyze` | POST | `{topics}` | `{advice}` |
| `/agent/ping` | GET | - | `{pong}` |
| `/webhook/task_result` | POST | `{task_id, status, result}` | `{ok}` |
| `/webhook/cookie` | POST | `{platform, cookie}` | `{ok}` |
| `/webhook/collect_data` | POST | `{platform, followers, likes}` | `{ok}` |

---

## 你照着做的顺序

1. **先试：** 打开影刀，找有没有"HTTP请求"这个积木
2. **告诉我结果：** 有还是没？
3. **有**→ 下载 `bridge.py` 在我这边跑起来，直接配HTTP请求
4. **没有**→ 我在电脑上装Python，用脚本方式调
5. **建流程1：** 登录小红书（这个一次性的）
6. **建流程2：** 发布图文笔记（核心流程）
7. **跑通测试：** 发一篇笔记试试
8. 再搞流程3和4
