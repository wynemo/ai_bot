from bs4 import BeautifulSoup
import re
import html

def clean_html(html_text):
    # 解码HTML实体
    text = html.unescape(html_text)

    # 使用BeautifulSoup清理
    soup = BeautifulSoup(text, 'html.parser')
    text = soup.get_text()

    # 移除多余空白
    text = ' '.join(text.split())

    # 移除特殊字符和控制字符
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)

    return text
