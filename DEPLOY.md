**部署与更新指南（针对镜像 ghuiqiao711/ewa, 使用 sqlite + 本地配置）**

推荐的宿主机目录结构（仓库根目录或部署目录）：

- deploy/
  - .env                # 生产环境变量（敏感，请勿提交）
  - local_settings.py   # 覆盖配置（敏感，请勿提交）
- data/
  - db.sqlite3          # SQLite 数据库文件（持久化）
- staticfiles/          # collectstatic 输出（持久化）
- media/                # 媒体文件（持久化）

快速开始（第一次部署）

1. 在宿主机上创建目录并把敏感文件放置到 `deploy/`，确保权限正确：

```bash
mkdir -p deploy data staticfiles media
# 把你的 .env 文件与 local_settings.py 放到 deploy/
```

2. 拉取镜像并启动服务：

```bash
docker-compose -f docker-compose.prod.yml up -d
```

更新镜像（安全流程，避免覆盖数据）

1. 备份 sqlite：

```bash
cp ./data/db.sqlite3 ./data/db.sqlite3.bak
```

2. 停止服务，拉取新镜像并重启：

```bash
docker-compose -f docker-compose.prod.yml pull web
docker-compose -f docker-compose.prod.yml stop web
docker-compose -f docker-compose.prod.yml up -d web
```

3. （可选）运行迁移与 collectstatic：

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate --noinput
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

回滚（如果更新后异常）

```bash
cp ./data/db.sqlite3.bak ./data/db.sqlite3
docker-compose -f docker-compose.prod.yml restart web
```

注意事项

- 强烈建议不要在生产中使用 SQLite；如流量或并发增加，请切换到 PostgreSQL 并使用外部持久化卷或托管数据库。  
- 不要把 `deploy/.env` 或 `deploy/local_settings.py` 提交到代码仓库；将其加入 `.gitignore`。  
- 若使用反向代理（如 nginx），请根据需要在 `docker-compose.prod.yml` 中添加 nginx 服务并挂载证书。  
