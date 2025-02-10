# 兼容 openai api 的机器人

一个基于 Telegram 的智能机器人，集成了对话、网页内容获取和搜索功能。
支持使用ollama，openai兼容的API

## 特点

- 基于 Python 3.12+ 开发
- 支持 Telegram Bot API
- 集成 DuckDuckGo 搜索
- 支持网页内容抓取
- 暂时不支持流式对话
- Docker 容器化部署

## 使用

- 在电报 @BotFather 那里创建一个机器人
- 获取到token后，保存，后续将`BOT_TOKEN`内容设置为它。
- 加入search与fetch两个命令：
```
search - 通过网络搜索, search by web
fetch - 获取网页信息
```


### 配置文件

`settings.env`中填写环境变量:

```env
BOT_TOKEN=你的Telegram Bot Token
API_URL=API地址，默认是黄皮衣的
API_SECRET=API密钥
MODEL_NAME=模型名称
```

### 启动方式

1. 直接运行:

```bash
# 设置环境变量 API_SECRET API_URL 等
pip install -r requirements.txt
python main.py
```

2. Docker compose 运行:

```bash
docker-compose up -d
```

### 机器人命令

- `/start` - 获取使用说明
- `/search [关键词]` - 搜索内容
- `/fetch [URL]` - 获取网页内容
- 群聊里 直接 @ 机器人 - 进行对话

## 依赖

- Python 3.12+
- beautifulsoup4
- duckduckgo-search
- httpx
- python-telegram-bot
