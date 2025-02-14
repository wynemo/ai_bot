import asyncio
import datetime
import json
import logging
import os
import re

import httpx
from duckduckgo_search import DDGS
from telegram import Update
from telegram.ext import (Application, CommandHandler, ContextTypes,
                          MessageHandler, filters)

import settings
from clean import clean_html

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
    os._exit(0)


# 处理被 @ 的消息
async def handle_mention(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                ddgs_gen = ddgs.text(
                    key_words,
                    safesearch="Off",
                    timelimit="y",
                    backend="lite",
                    max_results=20,
                )
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
                        response = await client.get(url, follow_redirects=True)
                        response_text = f"URL内容:\n{response.text}"
                        response_text = clean_html(response_text)
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
                "frequency_penalty": 0,
                "presence_penalty": 0,
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
                                    if len(current_message) >= 4000:
                                        await update.message.reply_text(current_message)
                                        current_message = ""
                            else:
                                print("-----------------", "no choices")
                        except Exception:
                            print("-----------------", "there is something wrong")
                            logging.exception(f"Error processing chunk: {chunk}")
                            continue
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
                        # Find last newline before 4000 chars
                        split_point = full_message[:4000].rfind("\n")
                        if split_point == -1:
                            split_point = 4000

                        # Send first part and update remaining message
                        await update.message.reply_text(full_message[:split_point])
                        full_message = full_message[split_point:].lstrip()

                    # Send remaining message if any
                    if full_message:
                        print("sending message", len(full_message))
                        await update.message.reply_text(full_message)


async def handle_mars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Implement Mars-related functionality here
    prompt = """首先你需要将句子的文字翻转，即编程中的字符串翻转，比如我会输入“亲父的他是谁”，你输出“谁是他的父亲”，你不要考虑翻转过后的句子是否通顺。
    然后你把句子文字转换为火星文，火星文通常会用一些不常见的字、近似字、繁体字、或类似字体来代替原有的字，
    比如“獨傢--婀里妑妑骉囩啝駦卂創始亾骉囮駦將傪咖蓙談浍--消息亾仕”，其实是“独家 — 阿里巴巴马云与腾讯创始人马化腾讲参加座谈会-消息人士”。
    火星文转换不能只用繁体字替换，不用考虑句子是否通顺，大概意思明白就行。
    无需深度推理，你需要快速处理我输入的文字："""
    input_words = update.message.text.strip("/mars")
    input_words = input_words.strip(BOT_NAME)

    # 这里可以调用你的 API
    async with httpx.AsyncClient(timeout=180) as client:
        url = f"{settings.API_URL}/chat/completions"
        # url = 'https://api.siliconflow.cn/v1/chat/completions'
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
            "messages": [{"role": "user", "content": prompt + input_words[::-1]}],
        }

        async with client.stream("POST", url, headers=headers, json=data) as response:
            current_message = ""
            async for chunk in response.aiter_lines():
                if chunk.startswith("data: "):
                    try:
                        chunk = chunk[6:]  # Remove 'data: ' prefix
                        if chunk.strip() == "[DONE]":
                            break
                        obj = json.loads(chunk)
                        if len(obj["choices"]) > 0:
                            content = obj["choices"][0]["delta"].get(
                                "content", ""
                            ) or obj["choices"][0]["delta"].get("reasoning_content", "")
                            if content:
                                # print(content)
                                current_message += content
                                if len(current_message) >= 4000:
                                    await update.message.reply_text(current_message)
                                    current_message = ""
                            else:
                                pass
                                # print(obj)
                        else:
                            print("-----------------", "no choices")
                    except Exception:
                        print("-----------------", "there is something wrong")
                        logging.exception(f"Error processing chunk: {chunk}")
                        continue
            if current_message:
                await update.message.reply_text(current_message)
            print("finished", len(current_message))


def main():
    # 创建应用
    application = Application.builder().token(TOKEN).build()

    # 添加处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", handle_mention))
    application.add_handler(CommandHandler("fetch", handle_mention))
    application.add_handler(CommandHandler("mars", handle_mars))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mention)
    )
    application.add_handler(
        MessageHandler(filters.TEXT & filters.Entity("mention"), handle_mention)
    )

    application.add_error_handler(error_handler)

    # 启动机器人
    print("机器人已启动...")
    application.run_polling()


if __name__ == "__main__":
    main()
