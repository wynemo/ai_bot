# 兼容 openai api 的机器人

一个基于 Telegram 的智能机器人，集成了对话、网页内容获取和搜索功能。
支持使用ollama，openai兼容的API
支持访问聊天内容中的url 获取上下文
支持youtube视频字幕总结

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
- 用setcommands 设置几个命令：
```
start - 开始
search - 命令后跟文字 通过网络搜索, search by web
fetch - 获取网页信息
mars - 命令后跟文字，转换为火星文
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
uv venv --python 3.12
uv run --env-file settings.env guard.py
```

2. Docker compose 运行:

```bash
docker-compose up -d
```

### 机器人命令

- `/start` - 获取使用说明
- `/search [关键词]` - 搜索内容
- `/fetch [URL]` - 获取网页内容
- `/mars [文字]` - 命令后跟文字，转换为火星文
- 群聊里 直接 @ 机器人 - 进行对话

## 依赖

- Python 3.12+
- beautifulsoup4
- duckduckgo-search
- httpx
- python-telegram-bot

## 视频讲解
[![视频讲解](https://img.youtube.com/vi/E5CH3p9w8UU/0.jpg)](https://www.youtube.com/watch?v=E5CH3p9w8UU)


## todo

1. ~~清理html有问题 更好的算法 https://www.foreignaffairs.com/united-states/path-american-authoritarianism-trump?continueFlag=ef3c5d6fc1ef621eb6fc041f2078ae4a 比如这个~~
2. ~~支持 youtube 视频字幕总结 参考 https://github.com/stong/tldw~~
3. 多轮对话
4. 重构，发消息那块，改为迭代器
5. 支持排除web搜索结果中的网站，比如知乎、csdn等
6. ~~支持 bilibili 视频字幕总结 https://github.com/Fros1er/bilibili-subtitle-to-text 参考 懒得做了 b站没啥用~~
7. 处理接受openai api时 网络请求错误的处理
8. 似乎并发有问题 https://github.com/python-telegram-bot/python-telegram-bot/wiki/Concurrency 原来默认没有支持并发 需要改参数 处理了一些了
9. 支持除了duckduckgo的其他搜索 比如tavily
10. 搜索报错的时候返回错误信息到聊天
11. 用一段时间老是接收不到消息 得排查bug
