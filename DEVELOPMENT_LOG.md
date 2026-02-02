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
- folk原作者仓库代码。


#### commit记录
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
