import os

API_URL = os.getenv('API_URL', 'https://integrate.api.nvidia.com/v1/chat/completions')
API_SECRET = os.getenv('API_SECRET')
BOT_TOKEN = os.getenv('BOT_TOKEN')
MODEL_NAME = os.getenv('MODEL_NAME', 'deepseek-ai/deepseek-r1')
