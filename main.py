import asyncio
import datetime
import json
import logging
import os
import re

import httpx
import primp
import requests
import telegram.error
from duckduckgo_search import DDGS
from telegram import Update
from telegram.ext import (Application, CommandHandler, ContextTypes,
                          MessageHandler, filters)

import settings
from clean import clean_html
from spark import convert
from youtube import get_video_caption

# 替换成你从 BotFather 获取的 token
TOKEN = settings.BOT_TOKEN
BOT_NAME = settings.BOT_NAME


# 处理 /start 命令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "你好！我是机器人，@我并发送消息，我会回复你。可以用/search 内容, /fetch 网页 这两个指令"
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("exit")
    logging.error("Exception while handling an update:", exc_info=context.error)
    if isinstance(context.error, telegram.error.NetworkError):
        # 不可恢复的,unrecoverable
        os._exit(0)


def get_html_content(url):
    if url.startswith('https://x.com') or url.startswith('https://fixupx.com'):
        url = url.replace('https://x.com', 'https://fixupx.com', 1)
        response = requests.get(url)
        return response.text
    if url.startswith('https://twitter.com') or url.startswith('https://fxtwitter.com'):
        url = url.replace('https://twitter.com', 'https://fxtwitter.com', 1)
        response = requests.get(url)
        return response.text
    client = primp.Client(
        impersonate="chrome_131",
        impersonate_os="windows",
        follow_redirects=True)
    if url.startswith('https://reddit.com'):
        client = primp.Client(
            impersonate=None,
            impersonate_os=None,
            headers = {"User-Agent": "Mozilla/5.0"},
            follow_redirects=True)
    response = client.get(url)
    response_text = f"URL内容:\n{response.text}"
    response_text = clean_html(response_text)
    return response_text


# 处理被 @ 的消息
async def handle_mention(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        print("no message")
        return
    # 确保消息中提到了机器人
    print(update.message.entities, update.message.text)
    for each in update.message.entities:
        print(each.type)
    if (
        update.message.chat.type == "private"
        or (
            update.message.entities
            and any(entity.type == "bot_command" for entity in update.message.entities)
        )
        or (
            update.message.entities
            and any(entity.type == "mention" for entity in update.message.entities)
            and BOT_NAME in update.message.text
        )
    ):
        ddgs_gen = None
        response_text = None
        refs = None
        if update.message.text.startswith("/search"):
            with DDGS() as ddgs:
                # 使用DuckDuckGo搜索关键词
                key_words = update.message.text.strip("/search")
                key_words = key_words.strip(BOT_NAME)
                print("keys words", key_words)
                if not key_words:
                    await update.message.reply_text("请输入搜索关键词")
                    return
                try:
                    ddgs_gen = await asyncio.to_thread(ddgs.text,
                        key_words,
                        safesearch="Off",
                        timelimit="y",
                        backend="lite",
                        max_results=20,
                    )
                except Exception as e:
                    await update.message.reply_text(f"搜索失败：{e}")
                    return
                refs = map(
                    lambda x: (
                        x["title"],
                        x["href"],
                    ),
                    ddgs_gen,
                )

        # 检查消息中是否包含 http 链接
        urls = re.findall(
            "http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
            update.message.text,
        )
        if urls:
            async with httpx.AsyncClient() as client:
                for url in urls:
                    try:
                        if url.startswith('https://www.youtube.com/watch?v=') or url.startswith('https://youtu.be/'):
                            response_text = await asyncio.to_thread(get_video_caption, url.strip())
                        else:
                            response_text = await asyncio.to_thread(get_html_content, url)
                        # print(response_text)
                    except Exception as e:
                        await update.message.reply_text(f"获取URL内容失败: {str(e)}")
                        return
                    # 现在就检查一个就行了
                    break

        # 这里可以调用你的 API
        async with httpx.AsyncClient(timeout=180) as client:
            url = f"{settings.API_URL}/chat/completions"
            # url = 'https://api.siliconflow.cn/v1/chat/completions'
            print(f"using {url} {settings.MODEL_NAME}")
            headers = {"authorization": f"Bearer {settings.API_SECRET}"}
            data = {
                "model": settings.MODEL_NAME,
                # "model": "deepseek-r1",
                "temperature": 0.4,
                "top_p": 1,
                # "frequency_penalty": 0,
                # "presence_penalty": 0,
                "n": 1,
                "stream": True,
                "messages": [
                    {"role": "user", "content": update.message.text + ", 用中文回复"}
                ],
            }
            if ddgs_gen:
                data["messages"].append(
                    {
                        "role": "system",
                        "content": f"""You are an AI model who is expert at searching the web and answering user\'s queries.
                            \\n\\nGenerate a response that is informative and relevant to the user\'s query based on provided search results.
                                the current date and time are {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:\n
                                {json.dumps(ddgs_gen)}
                                """,
                    }
                )
            elif response_text:
                data["messages"].append(
                    {
                        "role": "system",
                        "content": f"""You are an AI model who is expert at searching the web and answering user\'s queries.
                            \\n\\nGenerate a response that is informative and relevant to the user\'s query based on provided search results.
                                the current date and time are {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:\n
                                {response_text}
                                """,
                    }
                )
            else:
                data["messages"].append(
                    {
                        "role": "system",
                        "content": f"""You are an AI model who is expert at searching the web and answering user\'s queries.
                                            \\n\\nGenerate a response that is informative and relevant to the user\'s query based on provided search results.
                                                the current date and time are {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:\n
                                                """,
                    }
                )

            # f = open("test.txt", "wt")
            async with client.stream(
                "POST", url, headers=headers, json=data
            ) as response:
                print(response.status_code)
                current_message = ""
                async for chunk in response.aiter_lines():
                    if chunk.startswith("data: "):
                        try:
                            chunk = chunk[6:]  # Remove 'data: ' prefix
                            if chunk.strip() == "[DONE]":
                                continue
                            obj = json.loads(chunk)
                            if len(obj["choices"]) > 0:
                                content = obj["choices"][0]["delta"].get(
                                    "content", ""
                                ) or obj["choices"][0]["delta"].get(
                                    "reasoning_content", ""
                                )
                                if content:
                                    # f.write(content)
                                    current_message += content
                                    while len(current_message) >= 4000:
                                        await update.message.reply_text(
                                            current_message[:4000]
                                        )
                                        current_message = current_message[4000:]
                            else:
                                print("-----------------", "no choices")
                        except Exception:
                            print("-----------------", "there is something wrong")
                            logging.exception(f"Error processing chunk: {chunk}")
                            continue
                    else:
                        if response.status_code >= 400:
                            print("chuck is", chunk)
                print("finished")

                if current_message or refs:
                    full_message = current_message or ""
                    if refs:
                        links_message = "\n相关链接:\n"
                        for title, href in refs:
                            links_message += f"{title}: {href}\n"
                        full_message += links_message

                    # Split message if it exceeds 4000 characters
                    while len(full_message) > 4000:
                        # Send first 4000 chars and update remaining message
                        await update.message.reply_text(full_message[:4000])
                        full_message = full_message[4000:].lstrip()

                    # Send remaining message if any
                    if full_message:
                        # print("sending message", len(full_message))
                        await update.message.reply_text(full_message)
            # f.close()


async def handle_mars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        print("no message")
        return
    if update.message.entities and any(
        entity.type == "bot_command" for entity in update.message.entities
    ):
        input_words = update.message.text.replace("/mars", "", 1)
        input_words = input_words.replace(BOT_NAME, "", 1)
        if not input_words:
            await update.message.reply_text("请输入要转换的文字")
            return

        # Convert input words to Mars language
        mars_words = convert(input_words, 3)

        # Send converted message
        await update.message.reply_text(mars_words)


def get_text_iter(text):
    # 字符串超过4000， 需要分段发送，分段发送，每段不超过4000字节
    for i in range(0, len(text), 4000):
        yield text[i : i + 4000]


async def handle_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        print("no message")
        return
    if update.message.entities and any(
        entity.type == "bot_command" for entity in update.message.entities
    ):
        input_words = update.message.text.replace("/youtube", "", 1)
        input_words = input_words.replace(BOT_NAME, "", 1)
        # get youtube caption
        result = await asyncio.to_thread(get_video_caption, input_words.strip())
        if result:
            print(f"youtube caption length: {len(result)}")
            async for each in call_api(result):
                await update.message.reply_text(each)
        else:
            await update.message.reply_text("下载视频字幕失败")

async def call_api(user_text):
    # 这里可以调用你的 API
    async with httpx.AsyncClient(timeout=180) as client:
        url = f"{settings.API_URL}/chat/completions"
        print(f"using {url} {settings.MODEL_NAME}")
        headers = {"authorization": f"Bearer {settings.API_SECRET}"}
        data = {
            "model": settings.MODEL_NAME,
            "temperature": 0.4,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "n": 1,
            "stream": True,
            "messages": [
                {"role": "user", "content": user_text + ", 用中文回复"}
            ],
        }
        data["messages"].append(
            {
                "role": "system",
                "content": f"""You are an AI model who is expert at searching the web and answering user\'s queries.
                                    \\n\\nGenerate a response that is informative and relevant to the user\'s query based on provided search results.
                                        the current date and time are {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:\n
                                        """,
            }
        )


        async with client.stream(
            "POST", url, headers=headers, json=data
        ) as response:
            current_message = ""
            async for chunk in response.aiter_lines():
                if chunk.startswith("data: "):
                    try:
                        chunk = chunk[6:]  # Remove 'data: ' prefix
                        if chunk.strip() == "[DONE]":
                            continue
                        obj = json.loads(chunk)
                        if len(obj["choices"]) > 0:
                            content = obj["choices"][0]["delta"].get(
                                "content", ""
                            ) or obj["choices"][0]["delta"].get(
                                "reasoning_content", ""
                            )
                            if content:
                                current_message += content
                                while len(current_message) >= 4000:
                                    yield current_message[:4000]
                                    current_message = current_message[4000:]
                        else:
                            print("-----------------", "no choices")
                    except Exception:
                        print("-----------------", "there is something wrong")
                        logging.exception(f"Error processing chunk: {chunk}")
                        continue
            if current_message:
                yield current_message
            print("finished")


def main():
    # 创建应用
    application = Application.builder().token(TOKEN).build()

    # 添加处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", handle_mention))
    application.add_handler(CommandHandler("fetch", handle_mention))
    application.add_handler(CommandHandler("mars", handle_mars))
    application.add_handler(CommandHandler("youtube", handle_youtube))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mention, block=False)
    )
    application.add_handler(
        MessageHandler(filters.TEXT & filters.Entity("mention"), handle_mention, block=False)
    )

    application.add_error_handler(error_handler)

    # 启动机器人
    print("机器人已启动...")
    application.run_polling()


if __name__ == "__main__":
    main()
