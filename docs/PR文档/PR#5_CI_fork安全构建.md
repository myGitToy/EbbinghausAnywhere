# CI/CD Fork 安全构建：PR 镜像构建与上传

> **项目地址**：[EbbinghausAnywhere](https://github.com/myGitToy/EbbinghausAnywhere)
> **PR编号**：PR #5
> **创建日期**：2026-02-01
> **功能分支**：ci/docker-secrets-fix
> **目标分支**：main
> **合并日期**：2026-02-01
> **合并提交**：4acbdd1

## 功能概述

为开源项目的 Pull Request 工作流添加安全的 Docker 镜像构建机制，支持 fork 仓库的 PR 自动构建镜像并上传为 GitHub Actions Artifact，解决 fork 仓库无法推送镜像到上游 Docker Hub 的问题。

## 背景说明

### 开源项目的 CI 挑战

在开源项目中，外部贡献者通过 fork 仓库提交 PR，面临以下挑战：

1. **权限限制**：fork 仓库没有上游仓库的 Docker Hub 推送权限
2. **安全考虑**：不能将敏感的 Docker Hub 凭证暴露给 fork 仓库的 CI
3. **验证需求**：维护者需要在合并 PR 前验证 Docker 镜像构建是否成功
4. **效率问题**：如果每次都合并后才发现构建问题，会增加沟通成本

### 现有方案的局限性

**方案 1：仅 main 分支推送**

```yaml
- name: Build and push
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

- 问题：fork 的 PR 无法验证镜像构建
- 维护者需要在合并后才能发现构建问题

**方案 2：在 PR 中推送**

```yaml
- name: Build and push
  if: github.event_name == 'pull_request'
```

- 问题：fork 仓库没有 Docker Hub 推送权限
- 安全风险：不能将上游 Docker Hub 凭证暴露给 fork

### 设计目标

- **Fork 安全**：fork 仓库无需上游 Docker Hub 凭证即可构建
- **可验证性**：维护者可以在 PR 页面下载并测试镜像
- **成本优化**：使用 GitHub Actions Artifact 存储，无需外部 registry
- **自动清理**：Artifact 自动过期，节省存储空间

## 技术实现

### 1. Fork 安全的 PR 构建任务

**文件**：`.github/workflows/build.yml`

#### 新增独立 Job

```yaml
build-for-prs:
  name: Build (PR / fork safe)
  runs-on: ubuntu-latest
  if: github.event_name == 'pull_request'
  steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Build Docker image (no push)
      run: |
        IMAGE_TAG="eaw-pr-${{ github.sha }}"
        docker build -t "$IMAGE_TAG" .
        docker save "$IMAGE_TAG" -o "./${IMAGE_TAG}.tar"

    - name: Upload image tar artifact
      uses: actions/upload-artifact@v4
      with:
        name: docker-image-${{ github.sha }}
        path: ./eaw-pr-${{ github.sha }}.tar
```

**关键设计**：

1. **条件执行**：`if: github.event_name == 'pull_request'` 确保仅在 PR 时运行
2. **Fork 安全**：不需要任何 Docker Hub 凭证
3. **本地构建**：使用 `docker build` 仅构建镜像，不推送
4. **归档格式**：使用 `docker save` 导出为 tar 文件
5. **Artifact 上传**：使用 GitHub Actions Artifact 存储

### 2. 工作流架构

#### 完整的 CI 流程

```yaml
name: Build and Test

on:
  push:
    branches:
      - main
  pull_request:

jobs:
  # Job 1: 原有的构建任务（适用于 main 分支推送）
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: echo "Running tests..."

      - name: Check Docker secrets (only on main push)
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        run: |
          if [ -z "${{ secrets.DOCKER_USERNAME }}" ] || [ -z "${{ secrets.DOCKER_PASSWORD }}" ]; then
            echo "ERROR: DOCKER_USERNAME or DOCKER_PASSWORD secrets not set."
            exit 1;
          fi

      - name: Login to Docker Hub
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        uses: docker/login-action@v3

      - name: Build and push
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        uses: docker/build-push-action@v5

  # Job 2: 新增的 PR 构建任务（fork 安全）
  build-for-prs:
    name: Build (PR / fork safe)
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      # ... 构建和上传 Artifact
```

**Job 并行执行**：

- `build` 和 `build-for-prs` 可以并行运行
- PR 时只运行 `build-for-prs`
- Push 到 main 时只运行 `build` 的推送部分

### 3. Artifact 命名策略

**命名规则**：

```bash
# Artifact 名称
docker-image-{github.sha}

# 镜像标签
eaw-pr-{github.sha}

# 文件名
eaw-pr-{github.sha}.tar
```

**示例**：

```bash
# PR #123，commit SHA 为 abc123def
Artifact name: docker-image-abc123def
Image tag: eaw-pr-abc123def
File name: eaw-pr-abc123def.tar
```

**优势**：

- 唯一性：使用 commit SHA 避免命名冲突
- 可追溯性：可以从 Artifact 名称追溯到具体提交
- 自动清理：GitHub Actions Artifact 默认保留 90 天

### 4. PR 模板文件

**新增文件**：`pr_body.md`

虽然此 PR 添加了空文件，但为未来的 PR 模板预留了位置，可用于：

```markdown
## PR 描述

### 变更类型
- [ ] 新功能
- [ ] Bug 修复
- [ ] 重构
- [ ] 文档更新
- [ ] 性能优化

### 测试计划
- [ ] 单元测试通过
- [ ] 手动测试完成
- [ ] Docker 镜像构建成功

### 相关 Issue
Closes #(issue number)
```

## 使用说明

### 贡献者：提交 PR

#### Fork 仓库工作流

```bash
# 1. Fork 上游仓库
# 2. Clone 到本地
git clone https://github.com/your-username/EbbinghausAnywhere.git
cd EbbinghausAnywhere

# 3. 创建特性分支
git checkout -b feature-new-function

# 4. 进行修改
# ... 编写代码 ...

# 5. 提交更改
git add .
git commit -m "feat: add new function"

# 6. 推送到 fork
git push origin feature-new-function

# 7. 在 GitHub 上创建 PR
```

#### 自动构建触发

创建 PR 后，GitHub Actions 自动：

1. 检出代码（包括 PR 的变更）
2. 运行测试
3. 构建 Docker 镜像
4. 上传镜像为 Artifact

**无需任何额外配置**，fork 仓库也无需设置 Secrets。

### 维护者：验证 PR

#### 查看构建状态

在 PR 页面查看：

- **Checks** 标签页显示所有 CI 任务状态
- `build-for-prs` 任务显示构建是否成功
- 可以查看构建日志

#### 下载并测试镜像

**步骤 1**：下载 Artifact

1. 进入 PR 页面
2. 点击 Checks 标签
3. 滚动到 `build-for-prs` 任务
4. 点击 `Artifacts` 下拉菜单
5. 下载 `docker-image-{sha}`

**步骤 2**：加载镜像

```bash
# 解压 tar 文件
tar -xf eaw-pr-abc123def.tar

# 加载镜像到 Docker
docker load -i eaw-pr-abc123def.tar

# 查看加载的镜像
docker images | grep eaw-pr
```

**步骤 3**：运行测试

```bash
# 运行容器
docker run -d -p 8000:8000 eaw-pr-abc123def

# 访问测试
curl http://localhost:8000

# 或使用 docker-compose 测试
docker-compose -f docker-compose.yml up -d
```

#### 合并后行为

合并 PR 到 main 分支后：

1. GitHub Actions 自动构建并推送镜像到 Docker Hub
2. 标签为 `latest` 和 commit SHA
3. Artifact 不再需要，自动过期清理

## 边界情况处理

| 场景 | 处理策略 |
|------|----------|
| Fork 仓库没有 Secrets | CI 不需要任何 Docker Hub 凭证，正常构建 |
| PR 修改了 Dockerfile | 使用 PR 的 Dockerfile 构建，验证变更 |
| PR 修改了 `.dockerignore` | 使用 PR 的配置构建，确保安全规则 |
| 构建失败 | PR 显示失败状态，维护者可以看到错误日志 |
| Artifact 下载失败 | 可以重新触发工作流或在本地手动构建 |
| 多个 PR 同时构建 | 每个 PR 使用独立的 Artifact，不会冲突 |
| 90 天后 Artifact 过期 | 不影响已合并到 main 分支的镜像（在 Docker Hub） |

## 测试验证

### 场景 1：Fork 仓库提交 PR

#### 准备工作

```bash
# 1. Fork 上游仓库到你的 GitHub 账号
# 2. Clone fork 仓库
git clone https://github.com/your-username/EbbinghausAnywhere.git
cd EbbinghausAnywhere

# 3. 添加上游仓库
git remote add upstream https://github.com/myGitToy/EbbinghausAnywhere.git
```

#### 创建测试 PR

```bash
# 创建分支
git checkout -b test-ci-build

# 修改文件（添加注释）
echo "# Test CI build" >> README.md

# 提交并推送
git add README.md
git commit -m "test: verify CI fork-safe build"
git push origin test-ci-build

# 在 GitHub 上创建 PR
```

#### 验证构建

1. 访问 PR 页面
2. 检查 `build-for-prs` 任务状态
3. 确认没有要求配置 Docker Hub Secrets
4. 确认构建成功

### 场景 2：下载并测试 Artifact

```bash
# 1. 从 PR 页面下载 Artifact
# 2. 解压并加载
tar -xf eaw-pr-{sha}.tar
docker load -i eaw-pr-{sha}.tar

# 3. 运行容器
docker run -d -p 8000:8000 eaw-pr-{sha}

# 4. 测试访问
curl http://localhost:8000
```

### 场景 3：Dockerfile 变更验证

```bash
# 修改 Dockerfile
echo "# Test change" >> Dockerfile

# 提交 PR
git add Dockerfile
git commit -m "test: modify Dockerfile"
git push origin test-dockerfile-change

# 验证：
# 1. PR 构建成功
# 2. 下载 Artifact 并测试镜像
# 3. 确认 Dockerfile 变更生效
```

## 性能影响

### CI 执行时间

- **新增 Job**：`build-for-prs` 约 3-5 分钟
- **并行执行**：与 `build` Job 并行，不增加总时间
- **上传时间**：约 1-2 分钟（取决于镜像大小和网络）

### GitHub Actions 配额

- **免费额度**：公开仓库无限制
- **私有仓库**：每月 2000 分钟免费
- **Artifact 存储**：免费 500MB，保留 90 天

### 镜像大小优化

**当前镜像大小**：约 500MB

**优化建议**：

1. 使用多阶段构建减小镜像体积
2. 清理不必要的包和缓存
3. 使用 `alpine` 基础镜像

**示例**：

```dockerfile
# 多阶段构建
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["gunicorn", "EbbinghausAnywhere.wsgi:application"]
```

## 未来扩展

### 1. 自动化测试集成

在构建镜像后运行容器测试：

```yaml
- name: Run container tests
  run: |
    IMAGE_TAG="eaw-pr-${{ github.sha }}"
    docker run -d -p 8000:8000 "$IMAGE_TAG"
    sleep 10
    curl -f http://localhost:8000 || exit 1
```

### 2. 多架构支持

构建支持 ARM64、AMD64 等多架构的镜像：

```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3

- name: Build multi-arch image
  run: |
    docker buildx build \
      --platform linux/amd64,linux/arm64 \
      -t eaw-pr-${{ github.sha }} \
      --output type=tar,dest=./eaw-pr-${{ github.sha }}.tar \
      .
```

### 3. 镜像扫描集成

使用 Trivy 扫描镜像安全问题：

```yaml
- name: Build image
  run: |
    IMAGE_TAG="eaw-pr-${{ github.sha }}"
    docker build -t "$IMAGE_TAG" .

- name: Run Trivy scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: eaw-pr-${{ github.sha }}
    format: 'sarif'
    output: 'trivy-results.sarif'

- name: Upload Trivy results
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: 'trivy-results.sarif'
```

### 4. 自动评论 PR

构建完成后自动在 PR 中评论：

```yaml
- name: Comment PR with build info
  uses: actions/github-script@v6
  with:
    script: |
      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: '✅ Docker 镜像构建成功！\n\n下载 Artifact: https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }}'
      })
```

### 5. 定期清理旧 Artifact

添加定时任务清理过期的 Artifact：

```yaml
name: Cleanup old artifacts

on:
  schedule:
    - cron: '0 0 * * 0'  # 每周日午夜

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/github-script@v6
        with:
          script: |
            const artifacts = await github.rest.actions.listArtifactsForRepo({
              owner: context.repo.owner,
              repo: context.repo.repo,
            })
            // 删除 30 天前的 Artifact
```

## 相关文件

### 新增文件

- `pr_body.md` - PR 模板（预留）

### 修改文件

- `.github/workflows/build.yml` - 添加 fork 安全的 PR 构建任务

### 相关文档

- GitHub Actions Artifact 文档：https://docs.github.com/en/actions/using-workflows/storing-workflow-data-as-artifacts
- Docker 多阶段构建：https://docs.docker.com/develop/develop-images/multistage-build/
- Fork 仓库最佳实践：https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks

## 提交记录

```
commit 4acbdd1
Merge pull request #5 from myGitToy/ci/docker-secrets-fix

commit 9d800ed
CI: add fork-safe PR build job (build and upload image artifact)
```

## 版本信息

- **创建日期**：2026-02-01
- **功能分支**：ci/docker-secrets-fix
- **目标分支**：main
- **合并状态**：✅ 已合并
- **合并日期**：2026-02-01
- **合并提交**：4acbdd1
- **关联需求**：开源项目 Fork 友好 CI/CD
- **变更文件数**：2
- **总增加行数**：+23
- **总删除行数**：-0
- **总变更行数**：23

---

**维护者**：myGitToy
**审核状态**：已审核
**最后更新**：2026-02-10
