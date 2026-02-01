# Docker 部署指南

## 🚀 快速开始

### 1. 准备工作

确保服务器已安装：
- Docker (20.10+)
- Docker Compose (2.0+)

```bash
# 安装Docker和Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

### 2. 配置环境变量

编辑 `.env` 文件，确保包含以下配置：

```bash
# Django配置
SECRET_KEY=your_production_secret_key_here
DEBUG=False
ALLOWED_HOSTS=your_domain.com,www.your_domain.com,localhost

# 数据库配置（使用SQLite）
DATABASE_URL=sqlite:///db.sqlite3

# 如果使用PostgreSQL，使用以下配置：
# DATABASE_URL=postgres://ebbinghaus_user:your_secure_password_here@db:5432/ebbinghaus

# API密钥
BAIDU_API_KEY=your_baidu_api_key
BAIDU_SECRET_KEY=your_baidu_secret_key
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### 3. 构建和启动服务

```bash
# 构建镜像
docker-compose build

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f web
```

### 4. 初始化数据库

```bash
# 创建超级用户
docker-compose exec web python manage.py createsuperuser

# 查看迁移状态
docker-compose exec web python manage.py showmigrations
```

### 5. 访问应用

- **应用地址**: http://localhost 或 http://your_server_ip
- **管理后台**: http://localhost/admin

## 📦 常用命令

### 服务管理

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose stop

# 重启服务
docker-compose restart

# 停止并删除容器
docker-compose down

# 停止并删除容器、卷
docker-compose down -v
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f web
docker-compose logs -f db
docker-compose logs -f nginx
```

### 进入容器

```bash
# 进入Web容器
docker-compose exec web bash

# 进入数据库容器
docker-compose exec db psql -U ebbinghaus_user -d ebbinghaus
```

### Django管理命令

```bash
# 运行迁移
docker-compose exec web python manage.py migrate

# 创建超级用户
docker-compose exec web python manage.py createsuperuser

# 收集静态文件
docker-compose exec web python manage.py collectstatic --noinput

# 进入Django shell
docker-compose exec web python manage.py shell
```

### 数据库管理

```bash
# 备份数据库（SQLite）
docker-compose exec web python manage.py dumpdata > backup.json

# 恢复数据库
cat backup.json | docker-compose exec -T web python manage.py loaddata --format=json -

# 备份PostgreSQL（如果使用）
docker-compose exec db pg_dump -U ebbinghaus_user ebbinghaus > backup.sql

# 恢复PostgreSQL
cat backup.sql | docker-compose exec -T db psql -U ebbinghaus_user ebbinghaus
```

## 🔒 配置HTTPS（可选）

### 使用Let's Encrypt获取SSL证书

```bash
# 1. 修改nginx.conf和docker-compose.yml中的域名

# 2. 初次获取证书
docker-compose run --rm certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  -d your_domain.com \
  -d www.your_domain.com \
  --email your_email@example.com \
  --agree-tos \
  --no-eff-email

# 3. 在nginx.conf中启用HTTPS配置（取消注释）

# 4. 重启Nginx
docker-compose restart nginx
```

## 📊 性能优化

### 调整Worker数量

编辑 `Dockerfile` 中的Gunicorn配置：

```bash
# 计算公式: workers = (2 × CPU核心数) + 1
--workers 5  # 适用于2核CPU
```

### 启用Gzip压缩

在 `nginx.conf` 中添加：

```nginx
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_types text/plain text/css text/xml text/javascript 
           application/json application/javascript application/xml+rss;
```

## 🔧 故障排查

### 服务无法启动

```bash
# 查看详细错误
docker-compose logs web

# 检查容器状态
docker-compose ps

# 重新构建镜像
docker-compose build --no-cache
docker-compose up -d
```

### 静态文件404

```bash
# 重新收集静态文件
docker-compose exec web python manage.py collectstatic --noinput

# 检查权限
docker-compose exec web ls -la /app/staticfiles

# 重启Nginx
docker-compose restart nginx
```

### 数据库连接错误

```bash
# 检查数据库容器
docker-compose logs db

# 测试数据库连接
docker-compose exec db pg_isready -U ebbinghaus_user

# 重启数据库
docker-compose restart db
```

## 📝 生产环境检查清单

- [ ] 修改 `.env` 中的 `SECRET_KEY`
- [ ] 设置 `DEBUG=False`
- [ ] 配置正确的 `ALLOWED_HOSTS`
- [ ] 修改数据库密码（如使用PostgreSQL）
- [ ] 配置HTTPS证书
- [ ] 设置定期备份脚本
- [ ] 配置防火墙规则
- [ ] 启用日志轮转
- [ ] 监控磁盘空间
- [ ] 设置告警机制

## 🔄 更新应用

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 重新构建镜像
docker-compose build

# 3. 停止旧容器
docker-compose down

# 4. 启动新容器
docker-compose up -d

# 5. 运行迁移
docker-compose exec web python manage.py migrate

# 6. 收集静态文件
docker-compose exec web python manage.py collectstatic --noinput
```

## 🌐 多环境部署

### 开发环境

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### 生产环境

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 📞 技术支持

如遇问题，请查看：
- Docker日志: `docker-compose logs -f`
- 应用日志: `/app/debug.log`
- Nginx日志: `/var/log/nginx/`
