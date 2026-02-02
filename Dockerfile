# 使用Python 3.11作为基础镜像
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 可配置 APT 镜像（构建时可用 --build-arg 覆盖），默认使用阿里云镜像
ARG APT_MIRROR="http://mirrors.aliyun.com"

# 避免交互式安装导致阻塞
ENV DEBIAN_FRONTEND=noninteractive

# 设置工作目录
WORKDIR /app

# 安装系统依赖（使用可配置镜像、重试、强制 IPv4、并清理缓存）
RUN set -eux; \
        cp -a /etc/apt/sources.list /etc/apt/sources.list.bak || true; \
        if [ -f /etc/apt/sources.list ]; then \
            sed -i.bak -E "s#https?://([a-z0-9.-]*\.)?deb.debian.org/#${APT_MIRROR}/#g; s#https?://security.debian.org/#${APT_MIRROR}/#g" /etc/apt/sources.list || true; \
        fi; \
        if [ -d /etc/apt/sources.list.d ]; then \
            for f in /etc/apt/sources.list.d/*.list; do [ -f "$f" ] || continue; sed -i.bak "s#https?://([a-z0-9.-]*\.)?deb.debian.org/#${APT_MIRROR}/#g; s#https?://security.debian.org/#${APT_MIRROR}/#g" "$f" || true; done; \
        fi; \
        printf 'Acquire::Retries "3";\nAcquire::ForceIPv4 "true";\n' > /etc/apt/apt.conf.d/99docker-apt-config; \
        for i in 1 2 3; do apt-get update -o Acquire::Retries=3 -o Acquire::ForceIPv4=true && break || sleep 1; done; \
        apt-get install -y --no-install-recommends -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" \
            gcc curl ca-certificates; \
        apt-get clean; \
        rm -rf /var/lib/apt/lists/* /var/cache/apt/* || true

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
