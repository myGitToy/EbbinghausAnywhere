### 项目介绍

原项目为万物皆可艾宾浩斯，是一个基于Django和bootstrap的网页版记忆工具，支持桌面端和移动端访问，支持多用户登录并建立各自独立的数据集。通过Apache2.0协议开源，项目地址 https://github.com/BrandonLoh/EbbinghausAnywhere 

2026年我基于原项目做了深入的修改，添加了大语言模型的支持并深度优化了原先的遗忘曲线逻辑，也对代码的整体框架做了深度的重构和优化。

目前整个项目针对服务器部署做了许多适配和优化，支持Linux系统中进行docker compose部署，方便大家构建属于自己的网页服务，目前测试下来，一个班级40-50人的并发是完全没有问题的。

### 使用方法（摘要）

- 可在页面右上角弹出式菜单内选择相应功能。
- 设置类别和复习周期：在 Manage Data 选项可进入管理台页面，对 Category 和 Review Days 进行自定义设置，单词类别作为默认类别不能更改。
- 录入新条目：在 Input 页面可以录入新条目，选择日期和类别进行保存。输入时可通过冒号":"区分条目名称和内容，支持 MathJax 与 mhchem。
- 进行复习：在 Review 页面可以选择日期进行复习，默认为当日。点击条目可以选择 "Yes" "No" 来表示掌握程度，"Reset" 可将该条目复习周期重置为从当日开始。
- 导入和导出数据：在 Manage Profile 页面可以更改账号信息，导入和导出数据。

### 开发日志

### 2026-03-22 v0.3.6 词汇表系统（开发中）

- **词汇表资源库**：新增预置词汇资源系统，支持中考、高考等标准化词汇表
- **PDF 智能解析**：基于 pdfplumber 的解析器，支持中英对照 PDF 文件（如上海中考词汇默写本）
- **两级模型设计**：
  - VocabularyBook（词汇表元数据）：名称、等级、描述、系统提示词
  - VocabularyEntry（词汇条目）：原始数据字段（word_og, meaning_og, phonetic_og, example_og）+ AI 增强字段（uk_phonetic, us_phonetic）
- **星号标记支持**：保留 PDF 中的重点词汇标记（*、**、***）
- **Django 管理命令**：`python manage.py vocabulary_import_pdf <pdf_path>` 一键导入词汇表
- **AI 三级提示词配置**：词汇表级 > 用户级 > 系统默认，实现个性化例句生成
- **批量导入功能**：支持预览、多选、批量导入到学习记录，自动触发艾宾浩斯复习逻辑
- **去重机制**：导入时检查用户已存在的单词，避免重复创建
- **前端界面**：
  - 词汇表列表页：展示所有可用词汇表
  - 词汇表详情页：分页显示、多选、AI 增强和批量导入
- **导航栏集成**：在主导航栏添加词汇表入口
- **数据库迁移**：4 个迁移文件（0014-0017），完整记录模型演进
- **设计文档**：[docs/词汇表/设计文档.md](c:\Users\GHUIQ\repos\EbbinghausAnywhere\docs\词汇表\设计文档.md)（700+ 行详细设计）
- **技术栈**：Django + pdfplumber + DeepSeek API + Bootstrap 5

### 2026-02-11 v0.3.5 增加五子棋小游戏功能

- **React 五子棋游戏**：基于 create-react-app 构建的完整五子棋游戏，支持人机对战
- **AI 算法**：采用 Alpha-Beta 剪枝算法，提供简单/中等/困难三个难度级别
- **Django 集成**：通过 iframe 嵌入到 Django 模板，实现前后端分离
- **积分消费机制**：每局游戏消费 5 积分，点击"开始游戏"并确认后扣除
- **积分不足处理**：积分不足时显示友好提示，阻止游戏开始
- **跨窗口通信**：使用 window.postMessage 实现游戏与父页面的积分同步
- **静态文件优化**：配置相对路径（homepage: "."），确保在 iframe 子目录中正确加载资源
- **导航栏集成**：在主导航栏添加五子棋入口，带游戏手柄图标
- **完整测试覆盖**：
  - 静态文件测试（13 个测试用例，100% 通过率）
  - 积分系统测试（后端 8 个 + 前端 6 个测试用例）
- **新增测试文档**：GOBANG_TEST_REPORT.md、GOBANG_POINTS_TEST_REPORT.md
- **技术栈**：React 18 + Django + SQLite，采用 Git submodule 管理游戏源码

### 2026-02-08 v0.3.4 手机端适配优化

- 响应式布局深度优化：调整服务入口卡片从 col-md-3 改为 col-md-4，在桌面端显示3列，移动端显示2列；
- 手机端字体大小优化：h1 标题从 4rem 降至 2rem，h3 标题从 4rem 降至 1.75rem，提升小屏幕阅读体验；
- 导航栏优化：在侧边栏添加 Dict 快速入口，方便用户直接访问AI词典功能；
- 移动端卡片宽度调整：小屏幕下卡片宽度从60%优化至50%，改善触摸操作体验；

### 2026-02-08 v0.3.3 注册页面优化

- 邮箱字段改为可选，降低注册门槛；
- 优化表单字段值保留功能，用户提交失败后无需重新填写；
- 新增密码规则说明卡片，清晰展示密码要求（至少8位、非常见密码、非纯数字、不与个人信息相似）；
- 改进邮箱验证逻辑，仅在用户输入邮箱时才进行格式验证；
- 修复表单保存逻辑，使用 `.get()` 方法安全处理可选字段；
- 提升用户体验：移除必填星号，调整 placeholder 提示文本。
- 积分系统优化：将每日签到奖励从1分提升至5分，激励用户每日登录学习。

### 2026-02-07 v0.3.2 单词库分类

- 新增单词库分类管理功能，支持对单词进行多维度分类组织；
- 分类管理界面：提供分类的增删改查操作，支持自定义分类名称；
- 批量操作功能：支持将多个单词批量移动到指定分类；
- 移除默认分类限制：允许删除"单词"默认分类，删除时级联删除其下的所有单词；
- DeepSeek 查询界面集成：在保存单词时可直接选择目标分类；
- 新增数据模型：Category（分类模型）；
- 前端组件：新增 category-management.js（400+ 行），实现完整的分类管理交互逻辑；
- 模板更新：重构 list.html 和 deepseek_query.html，集成分类选择界面。

### 2026-02-07 v0.3.1 积分系统

- 新增积分系统，激励用户持续学习；
- 复习单词获得积分：每次复习成功获得1积分；
- 每日签到功能：每日签到可获得积分奖励；
- 连续学习奖励：连续学习/签到天数累计，触发额外奖励；
- 积分商城：支持兑换游戏时长（1积分=1分钟）；
- 积分历史记录：完整记录积分的获得和消费历史；
- 用户配置：支持自定义汇率、奖励开关等个性化设置；
- 新增数据模型：UserPoints、PointHistory、UserPointsConfig、PointRedemption、UserStreak；
- 完整的单元测试覆盖，包含模型测试、集成测试、API测试和边界测试；
- 添加积分系统设计文档和测试指南。

#### 2026-02-05 — TTS功能

- 添加浏览器TTS功能，支持用户切换发音选项；
- 查询和浏览页面增加美式英语和英式英语发音两种播放按钮；
- 增加TTS功能的参考文档；
- 优化普通用户发音体验（通过浏览器API提供发音服务）。

#### 2026-02-02 — 页面调整

- 在测试版中隐藏部分导航入口（Input / Search / Manage Profile / Manage Data）；
- 为公共用户添加开发日志页面（静态 Markdown 渲染）；
- 修复日历显示问题；
- 优化 review 逻辑；
- 修复 Dockerfile heredoc 问题、在缺失时自动生成 sources.list、支持 APT_MIRROR 与国内镜像，增强小内存构建兼容性；
- docker功能已基本调整完毕，一键部署测试成功。

#### 2026-02-01 — 逻辑修改

- 增强日历视图与复习计划展示；
- 重构遗忘曲线主逻辑；
- 引入 DeepSeek 进行释义，例句等功能；
- 主界面的功能和UI调整；
- 加强 CI、测试与自动化脚本。

#### 2025-04-03 — 逻辑修改

- 修正复习时间间隔的问题，原先版本必须要在复习日当天才能进行复习；
- 增加 docker 支持；
- 添加 pip install 与相关改动。

#### 2024-12-30 — 项目立项

- fork原作者仓库代码。

#### commit记录

- 2026-02-11 — Merge pull request #13 from myGitToy/feat_游戏_五子棋 (Hui Qiao) [b5caa2c]
- 2026-02-11 — 添加积分检查功能 (george) [acdaeba]
- 2026-02-11 — 更新积分通知系统 (george) [98098f5]
- 2026-02-11 — 修改控制台编码和调整调试文件 (george) [4165d1c]
- 2026-02-11 — 修改测试文件 (george) [6224c13]
- 2026-02-11 — 五子棋的积分扣除从原先的打开页面扣除，更改为点击开始并确认后，进行扣除 (Hui Qiao) [c7d6486]
- 2026-02-11 — 修改git ignore删除缓存js文件 (george) [b1e2029]
- 2026-02-11 — 修订AI搜索深度逻辑 (george) [fc378bb]
- 2026-02-11 — 更新项目经验文档 (george) [e52b2cb]
- 2026-02-11 — 重构建并渲染 (Hui Qiao) [7f64604]
- 2026-02-08 — Merge pull request #12 from myGitToy/feat_手机适配 (Hui Qiao) [7fa87db]
- 2026-02-08 — Merge branch 'main' into feat_手机适配 (Hui Qiao) [f49423c]
- 2026-02-08 — 更新至v0.3.3 (george) [caedc84]
- 2026-02-08 — Merge pull request #11 from myGitToy/feat_注册页面调整 (Hui Qiao) [90d0eb4]
- 2026-02-08 — feat: 更新Conda环境管理文档，增加在Bash中运行Python代码的解决方案和最佳实践 (george) [edec8fe]
- 2026-02-08 — feat: 调整注册页面，优化邮箱和姓名字段的处理，增加密码规则说明 (george) [6f56b37]
- 2026-02-07 — feat: 新增积分商城链接和强制部署方案 (Hui Qiao) [6314208]
- 2026-02-07 — Merge feat_单词库分类_v2: 合并单词库分类功能和积分系统 (Hui Qiao) [572016b]
- 2026-02-07 — feat: 在deepseek查询界面保存单词时增加分类选择功能 (george) [946db1c]
- 2026-02-07 — feat: 移除默认分类限制，允许删除'单词'分类并级联删除其下的单词 (george) [dc69820]
- 2026-02-07 — feat: 合并积分系统和单词库分类功能（第一个 commit: 分类管理与批量操作） (george) [954abe2]
- 2026-02-07 — Merge pull request #9 from myGitToy/feat_积分系统 (Hui Qiao) [7fc9b0c]
- 2026-02-07 — 增加claude文档 (george) [5e500b6]
- 2026-02-07 — 修正连续签到错误的问题 (george) [9ae37f3]
- 2026-02-07 — 增加积分系统的测试文档 (george) [a3936f7]
- 2026-02-07 — 增加积分商城和兑换功能 (Hui Qiao) [27ba048]
- 2026-02-07 — 增加和调整md文档位置 (Hui Qiao) [e72f6b5]
- 2026-02-07 — 修订开发日志 (Hui Qiao) [ecd9a17]
- 2026-02-05 — Merge pull request #8 from myGitToy/feat_tts (Hui Qiao) [342bfdc]
- 2026-02-05 — 添加浏览器tts功能，并提供用户切换选项 (george) [600f9da]
- 2026-02-05 — 增加tts的参考文档 (george) [582f025]
- 2026-02-05 — 更改说明文档的默认位置 (george) [99c413d]
- 2026-02-05 — 测试基于浏览器API提供的发音（普通用户无法正常使用谷歌发音） (george) [5f3fd42]
- 2026-02-05 — 查询和浏览页面增加美式英语和英式英语发音两种播放按钮 (Hui Qiao) [979e6e5]
- 2026-02-02 — 优化手机端卡片头部标题样式，减小字体和内边距以改善阅读体验 (george) [dfe404e]
- 2026-02-02 — 调整 DeepSeek 页面标题块，添加 HTML 标题标签以改善 SEO (george) [94796dc]
- 2026-02-02 — 更新开发日志，添加最近的提交记录 (george) [ab46274]
- 2026-02-02 — 调整侧边栏导航位置，将其从右侧改为左侧，并优化相关样式 (Hui Qiao) [1511dc0]
- 2026-02-02 — 调整复习页面表格的响应式处理，添加横向滚动支持并优化字体和内边距，适配手机页面 (Hui Qiao) [e9d84ef]
- 2026-02-02 — 调整测试版界面，合并服务项为一行并支持横向滚动，统一入口界面的各项元素 (Hui Qiao) [559f16a]
- 2026-02-02 — 调整测试版界面，隐藏部分功能入口，保留路由与页面，未来可以迅速恢复 (Hui Qiao) [89e6240]
- 2026-02-02 — 调整测试版导航项的注释格式，用于隐藏部分导航项 (Hui Qiao) [65bf8ad]
- 2026-02-02 — docs: 修正部署方法中的标题格式，增强可读性 (george) [1e6a5cd]
- 2026-02-02 — docs: 更新部署方法，添加本地和服务器部署步骤 (george) [5578fc1]
- 2026-02-02 — fix(docker): 避免 heredoc 导致 Dockerfile 解析错误，改用 printf 生成 sources.list (george) [b0d1f81]
- 2026-02-02 — fix(docker): 若缺少 sources.list 时生成基于 APT_MIRROR 的 sources.list，保证 apt update 指向国内镜像并可重试/强制 IPv4 (george) [78ecf13]
- 2026-02-02 — chore: 使用国内 apt 镜像并增强 apt 安装的稳定性 (新增 APT_MIRROR build-arg，重试/IPv4/清理) (george) [9d27653]
- 2026-02-02 — 修改docker打包文件，满足小内存构建需求 (Hui Qiao) [8f96e14]
- 2026-02-01 — 添加docker打包步骤的说明 (Hui Qiao) [8fed917]
- 2026-02-01 — Merge pull request #5 from myGitToy/ci/docker-secrets-fix (Hui Qiao) [4acbdd1]
- 2026-02-01 — CI: add fork-safe PR build job (build and upload image artifact) (george) [9d800ed]
- 2026-02-01 — Merge pull request #4 from myGitToy/ci/docker-secrets-fix (Hui Qiao) [884383f]
- 2026-02-01 — CI: only push docker on main, add secrets check; update .dockerignore to exclude .env and keys (george) [d6ecad7]
- 2026-02-01 — 修改逻辑说明文档 (george) [d322a8f]
- 2026-02-01 — Update Python version and add Docker steps in CI (Hui Qiao) [2a85b4f]
- 2026-02-01 — 配置自动化测试脚本 (george) [d55f62e]
- 2026-02-01 — Merge pull request #3 from myGitToy/feat_增加日历功能 (3150eba)
- 2026-02-01 — 修正日历渲染的问题 (george) [174b36a]
- 2026-02-01 — 增加日历视图中显示全部单词复习计划的功能 (george) [e97a9e8]
- 2026-02-01 — Safer unfamiliar_history filtering on YES: type-safe match only remove current-cycle records (george) [e416d1a]
- 2026-02-01 — Show unfamiliar_records count and dates in item detail review schedule (george) [38472d6]
- 2026-02-01 — Merge origin/main (allow unrelated histories) accept remote for conflicts (6854c10)
- 2026-02-01 — Merge pull request #2 from myGitToy/feat_遗忘曲线主逻辑变更 (277dda1)
- 2026-02-01 — chore: ignore sqlite backups (efd38c1)
- 2026-02-01 — feat: show reviewed_today, make feedback idempotent, update UI to mark reviewed and disable YES/NO (aaac356)
- 2026-02-01 — 配置和迁移自动化测试脚本 (b052093)
- 2026-02-01 — 添加单次点击NO的测试单元模块 (820646e)
- 2026-02-01 — 修复点击No以后，unfamily会在下个周期被重置的问题 (cf51e05)
- 2026-02-01 — 修复复习间隔显示不正常的问题 (0600181)
- 2026-02-01 — 创建遗忘曲线的逻辑说明文档，并且把原先的最后一个时间间隔点，即365天予以去除 (6b8382b)
- 2026-02-01 — 修正点击No以后，第二天复习时，Unfamiliar数量没有增加的问题 (86d5707)
- 2026-02-01 — 调整遗忘曲线的主逻辑 (709f0cd)
- 2026-02-01 — 增加点击单词列表，选择熟悉 不熟悉，会自动跳转到下一个单词的功能 (0486774 / 0638e0f)
- 2026-02-01 — 修复提交修改后，跳转逻辑出错的问题 (512ac1a / 8b2ba67)
- 2026-02-01 — 单词列表页面增加分页和默认只显示未复习单词的功能 (670e87d / c8ea1f6)
- 2026-02-01 — 增加docker部署的内容 (5bc7531 / f8c8553)
- 2026-02-01 — 修改.env文件的配置信息 (79bd36f / 79d0585)
- 2026-02-01 — Merge pull request #1 from myGitToy/feat_deepseek_claude4.5 (c122ad3 / b418263)
- 2026-02-01 — 修复一键导入 deepseek 中需要用户二次确认，且无 TTS 链接的问题 (c3151e2 / 26a3d2b)
- 2026-02-01 — 修正详细信息交互按钮可以展开，无法折叠的问题 (60e735f / d226013)
- 2026-02-01 — 增加在单词卡中能一键导入 deepseek 释义的功能 (1f6d9b6 / a985ef1)
- 2026-02-01 — 增加在单词卡中能一键导入 deepseek 释义的功能 (a985ef1)
- 2026-02-01 — 增加单词卡片的删改查功能 (a245b45 / 2017853)
- 2026-02-01 — 修改单词卡片中的 UI 呈现方式，保持和 deepseek 查询页面中一致 (1b8c7de / 02f2729)
- 2026-02-01 — deepseek 翻译的第一版，基本完成设想的架构和 UI (97e7fc5 / eae5470)
- 2026-02-01 — 添加百度翻译的支持（未全部实现） (c5080d3 / 7a1e6c5)
- 2025-04-03 — 添加 docker 说明 (1da38c4 / 738ab12)
- 2025-04-03 — 修正复习时间间隔的问题，修复必须要选择付息日当天才能进行复习的问题 (9254823 / 1c94f9d / 69d46c3)
- 2025-04-03 — 增加 docker 支持 (7a9afe2 / ca949a6)
- 2025-04-03 — 添加 pip install 与相关改动 (9b5dd19 / 904f262)
- 2025-01-09 — 版本标记 0.2.3.7 (904f262 / c9795e2)
- 2025-01-04 — 多个版本标签与发布记录（0.2.3.x, 0.2.2.x, 0.2.1.x 等）(904f262 等)
- 2024-12-30 — Update README.md / 初始版本发布 (18b5174 / c6da5e0 / 8fa39da)
- 2024-12-30 — Initial commit (4937f85 / e9697c5)