# Claude Code 项目记录

## Python 环境管理

### 项目本地 .conda 环境

本项目使用本地的 `.conda` 环境（Python 3.11.14）。

**快捷命令（已配置在 PowerShell Profile）**：

```powershell
# 激活项目 Python 环境
ea-act

# 切换到项目目录
ea-cd
```

**完整路径方式**（如果快捷命令不可用）：
本项目使用本地的 `.conda` 环境，Python版本为 3.11.14。

### 在 Bash 环境中运行 Python 代码

**问题**：在 Git Bash 或 MSYS2 环境中，`conda` 命令未初始化，无法直接使用 `python` 命令。

**解决方案**（按优先级排序）：

#### 方案1：直接使用本地 Python 可执行文件（推荐）

```bash
# 使用相对路径（最简洁）
./.conda/python.exe manage.py runserver

# 或使用绝对路径
/c/Users/GHUIQ/repos/EbbinghausAnywhere/.conda/python.exe manage.py runserver

# 其他 Django 命令
./.conda/python.exe manage.py check
./.conda/python.exe manage.py makemigrations
./.conda/python.exe manage.py migrate
./.conda/python.exe manage.py createsuperuser
./.conda/python.exe manage.py shell
```

**优点**：

- 无需激活环境
- 路径明确，避免混淆
- 适合自动化脚本和 CI/CD
- `./.conda/python.exe` 是最简洁的写法（推荐）

#### 方案2：使用 PowerShell 并激活环境

```powershell
# 在 PowerShell 中激活环境
conda activate "C:\Users\GHUIQ\repos\EbbinghausAnywhere\.conda"

# 然后正常运行
python manage.py runserver
```

**注意**：不能使用 `conda activate .conda`，必须使用完整路径。

#### 方案3：在 Bash 中设置临时别名

```bash
# 在当前 Bash 会话中设置别名
alias python='./.conda/python.exe'
alias pip='./.conda/Scripts/pip.exe'

# 然后正常使用
python manage.py runserver
pip list
```

**注意**：此方法仅在当前 Bash 会话中有效。

#### 方案4：修改 PATH 环境变量（会话级别）

```bash
# 添加 .conda 到 PATH（仅当前会话）
export PATH="/c/Users/GHUIQ/repos/EbbinghausAnywhere/.conda:/c/Users/GHUIQ/repos/EbbinghausAnywhere/.conda/Scripts:$PATH"

# 然后正常使用
python manage.py runserver
```

### 最佳实践

1. **开发调试**：使用方案1（直接调用 python.exe），最可靠
2. **交互式工作**：使用方案2（PowerShell + conda activate）
3. **编写脚本**：使用方案1或方案3（别名）
4. **自动化测试/CI**：使用方案1（明确路径）

### 验证环境

```bash
# 检查 Python 版本
./.conda/python.exe --version

# 检查已安装的包
./.conda/Scripts/pip.exe list

# 检查 Django 配置
./.conda/python.exe manage.py check
```

### 常见问题

**Q: 为什么不用 `python` 命令？**
A: 在 Git Bash 中，`python` 通常指向 Windows Store 的 Python stub，不是项目的 .conda 环境。

**Q: 可以全局激活 .conda 环境吗？**
A: 不建议。.conda 是项目本地环境，使用相对路径或明确路径更安全。

**Q: 如何在 VS Code 中配置？**
A: 在 `.vscode/settings.json` 中设置：

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.conda/python.exe"
}
```

### 激活项目本地 .conda 环境（PowerShell）

在 PowerShell 中激活时，不能使用 `conda activate .conda`，需要使用完整路径：

---

## React 应用部署到 Django 静态目录

### 项目结构

- **React 源码**：`external/gobang/` - 使用 create-react-app 构建
- **部署位置**：`static/gobang/` - Django 静态文件目录
- **访问方式**：通过 iframe 嵌入 Django 模板

### 常见问题：静态资源路径 404

**问题**：React 应用构建后的 `index.html` 使用绝对路径（如 `/static/js/main.xxx.js`），导致在 Django 静态子目录下无法加载资源。

**原因**：React 默认假设应用部署在根路径，但本项目部署在 `/static/gobang/` 子目录。

**解决方案**：

1. **在 `external/gobang/package.json` 中添加 `homepage` 字段**：

```json
{
  "name": "gobang-v3",
  "homepage": ".",
  ...
}
```

2. **重新构建应用**：

```bash
cd external/gobang
npm run build
```

3. **复制到 Django 静态目录**：

```bash
cp -r build/* ../../static/gobang/
```

### 验证修复

检查 `static/gobang/index.html` 中的资源引用：

```html
<!-- 错误：绝对路径 -->
<script src="/static/js/main.xxx.js"></script>

<!-- 正确：相对路径 -->
<script src="./static/js/main.xxx.js"></script>
```

### 开发工作流

修改 React 应用后的完整流程：

1. 在 `external/gobang/` 中开发和测试
2. 运行 `npm run build` 构建生产版本
3. 复制 `build/*` 到 `static/gobang/`
4. 刷新 Django 页面验证

### 注意事项

- `homepage: "."` 使构建输出使用相对路径，适用于子目录部署
- 每次修改 React 代码后都需要重新构建和复制
- 确保复制时覆盖旧文件（使用 `cp -r` 或删除后复制）
