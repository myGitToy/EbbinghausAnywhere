# Docker 生产环境部署与密钥安全

> **项目地址**：[EbbinghausAnywhere](https://github.com/myGitToy/EbbinghausAnywhere)
> **PR编号**：PR #7
> **创建日期**：2026-02-03
> **功能分支**：ci/docker-secrets-fix
> **目标分支**：main
> **合并日期**：2026-02-03
> **合并提交**：02ac5b0

## 功能概述

完善 Docker 容器化部署方案，增加生产环境部署文档，优化敏感信息管理，使用宿主机路径挂载方式实现数据持久化，确保密钥和配置文件安全性。

## 背景说明

### 部署痛点

在项目推广使用过程中，用户需要便捷的部署方案：

1. **配置安全**：如何安全地管理 `.env` 文件和 `local_settings.py`，避免泄露敏感信息
2. **数据持久化**：SQLite 数据库、静态文件、媒体文件需要在容器重启后保留
3. **更新流程**：如何安全地更新镜像而不覆盖现有数据
4. **快速部署**：用户希望通过简单命令即可启动服务

### 设计目标

- **安全优先**：敏感文件不打包进镜像，通过只读挂载方式注入
- **数据持久化**：数据库和用户数据存储在宿主机
- **操作简便**：提供完整的部署文档和示例配置
- **易于维护**：支持一键更新和回滚

## 技术实现

### 1. 生产环境 Compose 文件

**新增文件**：`docker-compose.prod.yml`

```yaml
version: '3.8'

services:
  web:
    image: ghuiqiao711/ewa:latest
    container_name: ewa_web
    restart: always
    env_file:
      - ./deploy/.env
    volumes:
      # 本地配置文件（不要把这些文件打包到镜像）
      - ./deploy/local_settings.py:/app/EbbinghausAnywhere/local_settings.py:ro
      - ./deploy/.env:/app/.env:ro
      # 持久化 SQLite 数据
      - ./data/db.sqlite3:/app/db.sqlite3
      # 媒体与静态文件
      - ./staticfiles:/app/staticfiles
      - ./media:/app/media
    ports:
      - "8000:8000"
    command: /app/entrypoint.sh
```

**设计要点**：

1. **镜像版本**：使用预构建的 `ghuiqiao711/ewa:latest` 镜像
2. **配置注入**：`.env` 和 `local_settings.py` 只读挂载（`:ro`）
3. **数据持久化**：SQLite 数据库文件映射到宿主机
4. **自动重启**：`restart: always` 确保服务稳定运行
5. **端口映射**：容器内 8000 端口映射到宿主机 8000 端口

### 2. 推荐目录结构

**宿主机目录布局**：

```
EbbinghausAnywhere/
├── deploy/              # 敏感配置目录（不提交到 Git）
│   ├── .env            # 环境变量
│   └── local_settings.py  # 本地配置覆盖
├── data/               # 数据持久化目录
│   └── db.sqlite3      # SQLite 数据库文件
├── staticfiles/        # 静态文件收集输出
├── media/              # 用户上传的媒体文件
└── docker-compose.prod.yml  # 生产环境 Compose 文件
```

**`.gitignore` 配置**：

```
deploy/
data/
staticfiles/
media/
```

### 3. 完整部署文档

**新增文件**：`DEPLOY.md`

#### 快速开始（第一次部署）

**步骤 1**：创建目录结构

```bash
mkdir -p deploy data staticfiles media
```

**步骤 2**：准备敏感文件

将 `.env` 和 `local_settings.py` 放入 `deploy/` 目录。

**`.env` 示例**：

```bash
DEBUG=False
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=your-domain.com,localhost
```

**`local_settings.py` 示例**：

```python
# 生产环境特定配置
DEBUG = False
ALLOWED_HOSTS = ['your-domain.com', 'localhost']

# 数据库配置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/app/db.sqlite3',
    }
}
```

**步骤 3**：启动服务

```bash
docker-compose -f docker-compose.prod.yml up -d
```

#### 更新镜像流程

**步骤 1**：备份数据库

```bash
cp ./data/db.sqlite3 ./data/db.sqlite3.bak
```

**步骤 2**：停止并更新服务

```bash
docker-compose -f docker-compose.prod.yml pull web
docker-compose -f docker-compose.prod.yml stop web
docker-compose -f docker-compose.prod.yml up -d web
```

**步骤 3**：运行迁移（可选）

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate --noinput
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

#### 回滚流程

如果更新后出现问题：

```bash
cp ./data/db.sqlite3.bak ./data/db.sqlite3
docker-compose -f docker-compose.prod.yml restart web
```

### 4. 密钥管理最佳实践

#### 敏感文件保护

1. **`.env` 文件**：
   - 包含：`SECRET_KEY`、数据库密码、API 密钥等
   - 权限：`chmod 600 deploy/.env`
   - 位置：宿主机 `deploy/` 目录，只读挂载到容器

2. **`local_settings.py` 文件**：
   - 包含：生产环境特定配置、数据库连接信息
   - 权限：`chmod 600 deploy/local_settings.py`
   - 位置：宿主机 `deploy/` 目录，只读挂载到容器

3. **证书文件**（如使用 HTTPS）：
   - 位置：`deploy/certs/` 目录
   - 权限：`chmod 600 deploy/certs/*`
   - 挂载：`./deploy/certs:/app/certs:ro`

#### Git 忽略配置

确保 `.gitignore` 包含：

```
# 敏感配置
deploy/
.env
local_settings.py

# 数据文件
data/
*.sqlite3
*.sqlite3-journal

# 用户生成内容
staticfiles/
media/
```

### 5. 安全注意事项

#### 当前方案限制

文档中明确指出：

> **强烈建议不要在生产中使用 SQLite；如流量或并发增加，请切换到 PostgreSQL 并使用外部持久化卷或托管数据库。**

**SQLite 限制**：
- 并发写入能力有限
- 不适合高流量场景
- 单机部署，无法横向扩展

#### 生产环境建议

1. **数据库升级**：
   - 切换到 PostgreSQL 或 MySQL
   - 使用托管数据库服务（如 AWS RDS、阿里云 RDS）
   - 或使用 Docker 容器运行数据库并使用数据卷

2. **反向代理**：
   - 使用 Nginx 或 Caddy 作为反向代理
   - 启用 HTTPS（Let's Encrypt）
   - 配置静态文件缓存

3. **监控和日志**：
   - 配置日志收集
   - 设置容器健康检查
   - 配置告警机制

4. **备份策略**：
   - 定期备份数据库
   - 备份用户上传的媒体文件
   - 备份配置文件（不含敏感信息）

## 使用说明

### 本地开发部署

对于本地开发，使用原有的 `docker-compose.yml`：

```bash
docker-compose up -d
```

### 生产服务器部署

#### 场景 1：使用预构建镜像

```bash
# 克隆仓库
git clone https://github.com/myGitToy/EbbinghausAnywhere.git
cd EbbinghausAnywhere

# 创建目录结构
mkdir -p deploy data staticfiles media

# 上传配置文件到 deploy/ 目录
# scp .env local_settings.py user@server:/path/to/EbbinghausAnywhere/deploy/

# 启动服务
docker-compose -f docker-compose.prod.yml up -d
```

#### 场景 2：使用自建镜像

如果不想使用公共镜像：

1. 修改 `docker-compose.prod.yml`：

```yaml
web:
  image: your-registry/ewa:latest  # 替换为你的镜像
  # 其他配置不变
```

2. 构建并推送镜像：

```bash
docker build -t your-registry/ewa:latest .
docker push your-registry/ewa:latest
```

### 配置验证

启动服务后，验证配置：

```bash
# 检查容器状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 进入容器
docker-compose -f docker-compose.prod.yml exec web bash

# 检查数据库
docker-compose -f docker-compose.prod.yml exec web python manage.py check

# 运行迁移
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate --noinput

# 收集静态文件
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

## 边界情况处理

| 场景 | 处理策略 |
|------|----------|
| 容器启动失败 | 检查日志 `docker-compose logs`，验证挂载路径和权限 |
| 数据库文件损坏 | 从备份恢复 `cp db.sqlite3.bak db.sqlite3` |
| 配置文件权限问题 | 确保敏感文件权限为 `600`，挂载为只读 `:ro` |
| 端口冲突 | 修改 `docker-compose.prod.yml` 中的端口映射 |
| 镜像拉取失败 | 检查网络连接，或使用本地镜像构建 |
| 静态文件丢失 | 重新运行 `collectstatic` 命令 |
| 宿主机磁盘空间不足 | 定期清理日志和临时文件，扩容磁盘 |

## 测试验证

### 部署测试清单

#### 基础功能测试

- [ ] 容器成功启动，状态为 `Up`
- [ ] Web 服务可访问（`http://localhost:8000`）
- [ ] 数据库文件持久化到宿主机
- [ ] 配置文件正确挂载到容器
- [ ] 敏感文件不在镜像中（`docker exec ewa_web ls /app` 检查）

#### 数据持久化测试

- [ ] 创建测试数据
- [ ] 重启容器 `docker-compose restart web`
- [ ] 数据仍然存在

#### 安全性测试

- [ ] `.env` 文件权限为 600
- [ ] `local_settings.py` 文件权限为 600
- [ ] 敏感文件未提交到 Git（检查 `.gitignore`）
- [ ] 配置文件为只读挂载（`:ro`）

#### 更新流程测试

- [ ] 备份数据库
- [ ] 拉取新镜像
- [ ] 重启服务
- [ ] 数据和配置保持不变

### 性能测试

- [ ] 容器启动时间 < 30 秒
- [ ] 页面响应时间 < 2 秒（静态页面）
- [ ] 数据库查询性能正常

## 性能影响

### 容器资源占用

- **内存**：基础镜像约 200-300MB
- **磁盘**：镜像约 500MB，数据文件根据使用情况增长
- **CPU**：根据并发用户数量动态调整

### 网络性能

- 使用桥接网络，性能损耗极小
- 静态文件由 Django 处理，建议生产环境使用 Nginx

### 数据库性能

- SQLite 适合小规模部署（< 50 并发用户）
- 建议生产环境切换到 PostgreSQL

## 未来扩展

### 数据库升级方案

**迁移到 PostgreSQL**：

1. 修改 `docker-compose.prod.yml`：

```yaml
services:
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: ewa
      POSTGRES_USER: ewa
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  web:
    depends_on:
      - db
    # 其他配置
    environment:
      DATABASE_URL: postgres://ewa:${DB_PASSWORD}@db:5432/ewa

volumes:
  postgres_data:
```

2. 迁移数据：

```bash
# 从 SQLite 导出数据
docker-compose -f docker-compose.prod.yml exec web python manage.py dumpdata > backup.json

# 切换到 PostgreSQL

# 导入数据
docker-compose -f docker-compose.prod.yml exec web python manage.py loaddata backup.json
```

### 反向代理配置

**添加 Nginx 服务**：

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./deploy/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./deploy/certs:/etc/nginx/certs:ro
      - ./staticfiles:/app/staticfiles:ro
      - ./media:/app/media:ro
    depends_on:
      - web
```

### 自动化部署

1. **CI/CD 集成**：
   - GitHub Actions 自动构建镜像
   - 自动推送到 Docker Hub
   - 部署脚本自动拉取最新镜像

2. **监控告警**：
   - 集成 Prometheus + Grafana
   - 配置容器健康检查
   - 设置异常告警

3. **备份自动化**：
   - 定时备份数据库
   - 自动上传到云存储
   - 备份验证和恢复测试

## 相关文件

### 新增文件

- `docker-compose.prod.yml` - 生产环境 Compose 配置
- `DEPLOY.md` - 部署与更新指南

### 修改文件

- `README.md` - 添加服务器部署章节

### 配置文件

- `.env` - 环境变量（不提交）
- `local_settings.py` - 本地配置（不提交）

## 提交记录

```
commit 02ac5b0
Merge pull request #7 from myGitToy/ci/docker-secrets-fix

commit b835b7e
Merge branch 'main' into ci/docker-secrets-fix

commit 9c08117
Add docker-compose.prod.yml (image ghuiqiao711/ewa) and DEPLOY.md with host-path plan

commit c337207
增加服务器部署的说明
```

## 版本信息

- **创建日期**：2026-02-03
- **功能分支**：ci/docker-secrets-fix
- **目标分支**：main
- **合并状态**：✅ 已合并
- **合并日期**：2026-02-03
- **合并提交**：02ac5b0
- **关联需求**：生产环境部署方案
- **变更文件数**：3
- **总增加行数**：+100
- **总删除行数**：-0
- **总变更行数**：100

---

**维护者**：myGitToy
**审核状态**：已审核
**最后更新**：2026-02-10
