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

---

## 实际部署记录（2026-10-01，study-hub #72）

- **部署目录**：`~/ewa-prod/`（独立于仓库，含 `docker-compose.prod.yml` 副本 + `deploy/` + `data/` + `staticfiles/` + `media/`），仓库工作区零运行时污染；
- **端口**：宿主机 **8095** → 容器 8000（原规划 8000 已被 HMU 后端占用）；
  - `deploy/local_settings.py` 覆盖 `CSRF_TRUSTED_ORIGINS`（8095 各 origin + 门户 8092）——绑定页表单 POST 需要；
  - study-hub 侧 `FederatedApp.ewa` 的 entryUrl/bridgeUrl 已同步改为 `http://192.168.1.155:8095/sso/bridge/`；
- **`deploy/.env`**：`SECRET_KEY`（随机）、`STUDY_HUB_URL=http://192.168.1.155:8090`、`STUDY_HUB_APP_SECRET`（= study-hub `data/FEDERATED-APPS.txt` 登记值）、`ALLOWED_HOSTS=192.168.1.155,localhost,127.0.0.1`（DEBUG 默认 False）。

### 换机重建步骤（镜像不推 Docker Hub，本地构建）

```bash
# 1. 源码 + 本目录的 data/db.sqlite3（每日随 study-hub 备份到 ewa-* 快照）
git clone https://github.com/myGitToy/EbbinghausAnywhere.git && cd EbbinghausAnywhere
docker build -t ghuiqiao711/ewa:latest .
# 2. 恢复 ~/ewa-prod 目录结构（deploy/.env 与 local_settings.py 需从备份/密码管理器取回）
# 3. 启动：cd ~/ewa-prod && docker compose -f docker-compose.prod.yml up -d
```

### 日常更新

```bash
cd ~/repos/EbbinghausAnywhere && git pull && docker build -t ghuiqiao711/ewa:latest .
cp ~/ewa-prod/data/db.sqlite3 ~/ewa-prod/data/db.sqlite3.bak
cd ~/ewa-prod && docker compose -f docker-compose.prod.yml up -d --force-recreate
```
