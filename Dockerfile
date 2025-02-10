# 使用 Python 3.12 作为基础镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装 uv
RUN pip install uv

# 复制项目文件
COPY pyproject.toml uv.lock ./

RUN uv venv

# 使用 uv 安装依赖
RUN uv pip install --no-cache .

# 复制源代码
COPY . .

# 运行 bot
CMD ["uv", "run", "main.py"]
