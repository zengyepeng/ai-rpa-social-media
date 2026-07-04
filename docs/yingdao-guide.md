# 影刀RPA 攻略 & 集成方案

## 一、影刀 RPA 能力清单

### 已确认的积木
| 分类 | 积木 | 用途 |
|------|------|------|
| 网页自动化 | 打开网页 | 打开小红书、浏览器等 |
| 网页自动化 | 点击元素(web) | 点击任何网页元素 |
| 网页自动化 | 填写输入框(web) | 向输入框填文字 |
| 网页自动化 | 鼠标悬停在元素上(web) | 触发hover效果 |
| 网页自动化 | 获取已打开的网页对象 | 多标签页切换 |
| 网页自动化 | 关闭网页 | 关闭页面 |
| 网页自动化 | 激活浏览器用户/环境 | 切换浏览器配置 |
| 其他 | 插入代码段(Python) | 运行任意Python代码 |
| 流程控制 | 条件判断、循环、等待 | 流程逻辑 |

### 关键发现：变量传递
- **Python代码段中的变量 → 影刀流程中直接用**
  - 需打开「Python模式」
  - 变量名要手动输入（不从列表选择）
- **全局变量**：Python中用 `glv["变量名"] = 值` 设置
- **print打印**：新版直接 `print()`，旧版要 `from xbot import print`
- **调用Python模块**：可新建 .py 模块文件，调用模块中的 `main()` 函数

### 缺少的关键积木
- ❌ 没有「HTTP请求」积木（确认中）
- ❌ 没有「JSON解析」积木
- ✅ 有「Python脚本」= 插入代码段(Python)

## 二、绕过方案：用Python代码段代替HTTP+JSON

### 方案A：直接Python请求云服务器
```python
import json
import urllib.request

# 问云服务器要AI文案
url = "http://43.140.208.144:8889/cmd/get_content"
data = json.dumps({"topic": "今天发什么", "cmd_id": 1}).encode("utf-8")
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=10)
result = json.loads(resp.read().decode("utf-8"))
content = result.get("data", {}).get("content", "没拿到文案")

# 存为影刀可用变量（注意：格式化为变量输出）
# Python代码段中定义的变量 = 影刀可直接使用的变量
ai_content = content
```

### 方案B：本地生成文案（不依赖网络）
```python
import json

# 预置文案模板
content = """🔥【标题】暑假找兼职？这5个副业比打工强10倍！

正文：暑假不知道干嘛？躺平太无聊，打工又怕踩坑...
不如试试这几个副业，零基础也能月入3000+！

{文案内容}
#暑假兼职 #副业推荐 #大学生兼职 #搞钱"""
```

### 方案C：读本地文件（文案由本机生成）
```python
import json

with open("C:/Users/zengy/Desktop/today_content.json", "r", encoding="utf-8") as f:
    data = json.load(f)
title = data["title"]
content = data["content"]
tags = data["tags"]
```

## 三、小红书发布全流程（影刀版）

### 第1步：打开小红书创作者中心
**积木：打开网页**
- URL: `https://creator.xiaohongshu.com`
- 浏览器: 推荐Chrome/Edge

### 第2步：登录
- 第一次手动扫码登录
- 后续保持登录状态（浏览器缓存）

### 第3步：点击「发布笔记」
**积木：点击元素(web)**
- 捕获「发布笔记」按钮元素

### 第4步：获取AI文案
**积木：插入代码段(Python)**

### 第5步：填写标题
**积木：填写输入框(web)**
- 捕获标题输入框
- 填入值: `{title变量}`

### 第6步：填写正文
**积木：填写输入框(web)**
- 捕获正文编辑器
- 填入值: `{content变量}`

### 第7步：上传图片
**方法1：用影刀「选择文件」积木**（如果有的话）
**方法2：直接设置input标签的value**
**方法3：Python代码段模拟键盘操作**
```python
import pyautogui
import time
pyautogui.write("C:\\Users\\zengy\\Pictures\\1.jpg")
pyautogui.press("enter")
```

### 第8步：添加标签
**积木：填写输入框(web)**
- 找到标签输入框
- 填入 `{tags变量}`

### 第9步：点击发布
**积木：点击元素(web)**
- 捕获「发布」按钮

## 四、云服务器指令API

### 当前云服务器可用接口
| 接口 | 方法 | 说明 |
|------|------|------|
| /ping | GET | 健康检查 |
| /status | GET | 查看Agent状态 |
| /agent/register | POST | 注册Agent在线 |
| /agent/poll | POST | 轮询指令 |
| /agent/result | POST | 汇报执行结果 |
| /cmd/get_content | POST | 获取AI文案 |

### 返回数据格式
```json
// /cmd/get_content
{
  "code": 0,
  "data": {
    "title": "暑假兼职推荐！",
    "content": "完整的文案内容...",
    "tags": ["暑假", "副业", "兼职"],
    "topic": "今天发什么"
  }
}
```

## 五、如果网络不通的替代方案

### 方案1：文案直接在影刀Python代码段中生成
用DeepSeek API直接从影刀调用，不走云服务器中转：
```python
import json, urllib.request

API_KEY = "sk-7597..."
url = "https://api.deepseek.com/v1/chat/completions"
data = json.dumps({
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "写一篇小红书种草文案，关于暑假兼职"}]
}).encode("utf-8")
req = urllib.request.Request(url, data=data, headers={
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
})
resp = urllib.request.urlopen(req, timeout=30)
result = json.loads(resp.read().decode("utf-8"))
content = result["choices"][0]["message"]["content"]
```

### 方案2：微信传文案
我每天在微信上给你发一篇文案，你手动复制到流程里。

## 六、老板操作备忘

### 你的电脑信息
- 用户名: zengy
- 桌面路径: C:\Users\zengy\Desktop
- Python环境: D:\anaconda3
- 影刀已安装: 是
- PyAutoGUI: 装了（但agent连不上云服务器）
- 网络: 手机热点（运营商可能拦截非常用端口）

### 下一步最优方案
1. **影刀里搭流程** — 用「打开网页」+「插入代码段(Python)」+「填写输入框」+「点击元素」
2. **代码段里直接调DeepSeek API生成文案**（不走云服务器，避免网络问题）
3. **全部在本地完成**，只管搭好跑起来
