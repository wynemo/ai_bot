import os

API_URL = os.getenv('API_URL', 'https://integrate.api.nvidia.com/v1')
API_SECRET = os.getenv('API_SECRET')
BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_NAME = os.getenv('BOT_NAME')
MODEL_NAMES = os.getenv('MODEL_NAMES', 'deepseek-ai/deepseek-r1')
DEBUG = os.getenv('DEBUG', None)
