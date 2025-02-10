import datetime
import json
import re
import logging

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from duckduckgo_search import DDGS

from clean import clean_html
import settings

# 替换成你从 BotFather 获取的 token
TOKEN = settings.BOT_TOKEN

# 处理 /start 命令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('你好！我是机器人，@我并发送消息，我会回复你。可以用/search 内容, /fetch 网页 这两个指令')

# 处理被 @ 的消息
async def handle_mention(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 确保消息中提到了机器人
    print(update.message.entities, update.message.text)
    for each in update.message.entities:
        print(each.type)
    if update.message.chat.type == "private" or (
        update.message.entities and any(
            entity.type in ("mention", "bot_command",) for entity in update.message.entities
        )
    ):
        ddgs_gen = None
        response_text = None
        if update.message.text.startswith('/search'):
            with DDGS() as ddgs:
                # 使用DuckDuckGo搜索关键词
                key_words = update.message.text.strip('/search')
                key_words = key_words.strip('@zhangxiaolong_bot')
                print('keys words', key_words)
                if not key_words:
                    await update.message.reply_text("请输入搜索关键词")
                    return
                ddgs_gen = ddgs.text(key_words, safesearch='Off', timelimit='y', backend="lite", max_results=20)
        elif update.message.text.startswith('/fetch'):
            urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', update.message.text)
            # 检查消息中是否包含 http 链接
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
                        break
        # 这里可以调用你的 API
        async with httpx.AsyncClient(timeout=180) as client:
            url = f'{settings.API_URL}/chat/completions'
            # url = 'https://api.siliconflow.cn/v1/chat/completions'
            print(f"using {url} {settings.MODEL_NAME}")
            headers = {
                'authorization': f'Bearer {settings.API_SECRET}'
            }
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
                    {
                        "role": "user",
                        "content": update.message.text + ", 用中文回复"
                    }
                ]
            }
            if ddgs_gen:
                data['messages'].append({"role": "system",
                    "content": f"""You are an AI model who is expert at searching the web and answering user\'s queries.
                            \\n\\nGenerate a response that is informative and relevant to the user\'s query based on provided search results.
                                the current date and time are {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:\n
                                {json.dumps(ddgs_gen)}
                                """
                })
            elif response_text:
                data['messages'].append({"role": "system",
                    "content": f"""You are an AI model who is expert at searching the web and answering user\'s queries.
                            \\n\\nGenerate a response that is informative and relevant to the user\'s query based on provided search results.
                                the current date and time are {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:\n
                                {response_text}
                                """
                })


            async with client.stream('POST', url, headers=headers, json=data) as response:
                current_message = ""
                async for chunk in response.aiter_lines():
                    if chunk.startswith('data: '):
                        try:
                            chunk = chunk[6:]  # Remove 'data: ' prefix
                            if chunk.strip() == '[DONE]':
                                continue
                            obj = json.loads(chunk)
                            if len(obj['choices']) > 0:
                                content = obj['choices'][0]['delta'].get('content', '')
                                if content:
                                    current_message += content
                                    if len(current_message) >= 4000:
                                        await update.message.reply_text(current_message)
                                        current_message = ""
                        except Exception:
                            logging.exception(f"Error processing chunk: {chunk}")
                            continue

                if current_message:
                    await update.message.reply_text(current_message)

def main():
    # 创建应用
    application = Application.builder().token(TOKEN).build()

    # 添加处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", handle_mention))
    application.add_handler(CommandHandler("fetch", handle_mention))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mention))
    application.add_handler(MessageHandler(filters.TEXT & filters.Entity("mention"), handle_mention))

    # 启动机器人
    print("机器人已启动...")
    application.run_polling()

if __name__ == '__main__':
    main()
