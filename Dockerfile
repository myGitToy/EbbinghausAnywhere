# 使用Python 3.11作为基础镜像
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 避免交互式安装导致阻塞
ENV DEBIAN_FRONTEND=noninteractive

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
     gcc \
     curl \
     ca-certificates \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# 复制requirements.txt并安装Python依赖
COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt gunicorn

# 复制项目文件
COPY . .

# 创建静态文件目录
RUN mkdir -p staticfiles media

# 收集静态文件
RUN python manage.py collectstatic --noinput || true

# 创建启动脚本
RUN echo '#!/bin/bash\n\
echo "Waiting for services..."\n\
sleep 5\n\
echo "Running migrations..."\n\
python manage.py makemigrations --noinput\n\
python manage.py migrate --noinput\n\
echo "Collecting static files..."\n\
python manage.py collectstatic --noinput\n\
echo "Starting Gunicorn..."\n\
exec gunicorn EbbinghausAnywhere.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# 暴露端口
EXPOSE 8000

# 设置启动命令
ENTRYPOINT ["/app/entrypoint.sh"]
