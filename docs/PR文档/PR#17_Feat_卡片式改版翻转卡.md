# PR #17 · 卡片式改版：背单词翻转卡 + 列表页卡片网格

- 日期：2026-10-01 ｜ 状态：已开 PR #17
- 关联：study-hub 仓库 issue #82（三轮拷问定稿）、#81（前置 CSS 基线，PR#16 已合并）、本仓库 PR#16

## 背景

用户定方向「卡片式布局 + 卡片式背单词」。拷问定稿：一期只做复习 + 列表两页；翻转卡 Anki-lite（一次一卡、认识/不认识二档沿用现有端点）；正面自动发音（可关）；桌面保留表格「清单模式」可切换、移动端默认卡片；零新前端依赖（不引打包链）；深色模式不做。

## 改动

**1. 背单词 = 翻转卡模式（`review_day.html` + `review_home.html`）**
- `ReviewView` 新增 `card_items` 纯原始值列表，经 `json_script` 交给前端（词/音标/释义/周期标签/复习状态）；
- 卡片正面：分类徽章 + 大字单词（clamp 字号）+ 双音标 + 双音源发音按钮 + 翻面提示；背面：释义（`|safe` + MathJax 翻面后重排）+ 周期/录入/认识后日期；
- 判定：底部「认识/不认识」大按钮（拇指热区）复用 `/review-feedback/yes|no/`；RESET 收为次级图标按钮（保留 confirm）；
- 键盘：Space 翻面、→ 认识、← 不认识、R 重置（输入框聚焦/modal 打开时自动让位）；
- 手势：卡片区监听右滑=认识/左滑=不认识（阈值 60px，屏幕左右 30px 边缘豁免给系统返回手势；滑动吞掉后续 click 防误翻面）；
- 发音：正面自动播一次（Google TTS 静默降级——iOS 无手势时失败不提示），偏好存 localStorage `flashcard_autoplay`，偏好条加开关；手动发音按钮走原有 `playAudioWithAccent`（失败有提示）；
- 进度条 + 剩余计数；已点评条目自动跳过；本页全部完成出「已完成」状态 + 手动刷新按钮；完成后表格行样式/`data-reviewed-today` 与清单模式共享同步，积分 toast 正常弹出；
- 模式切换：「🎴 卡片 / 📋 清单」按钮组，localStorage `review_mode` 记忆，**默认：≤768px 卡片、桌面清单**（定稿）；
- 顺带修复：积分 toast 原定义在 `review_day.html` 行内脚本里——该脚本在 innerHTML 注入下**从不执行**（等于 AJAX 流程中积分 toast 从未显示过），已迁至真正运行的 `review_home.html`；`review_day.html` 的整段死脚本（另一套重复绑定）随之删除。

**2. 列表页 = 响应式卡片网格（`list.html` + `category-management.js`）**
- 5 列表格 → `col-12 col-sm-6 col-lg-4` 卡片网格（手机 1 列/平板 2 列/桌面 3 列）；卡片：勾选框、分类徽章、词链、双音标、录入/下次复习日期；
- 全选从表头移到网格上方独立控制条；分页/分类筛选逻辑不变；
- 批量操作条：桌面保持页内顶栏；**手机端固定底部**（拇指热区，`position:fixed; bottom:0`）；
- `category-management.js` 的 `loadItems/renderItems` 同步改为卡片渲染（AJAX 切分类与首屏同构）；JSON 端点补 `us_phonetic/uk_phonetic`；
- 缓存穿透：`styles.css` 与 `category-management.js` 引用加 `?v=82`——部署后老用户不会被旧缓存卡住（本次实测踩到的真实问题）。

## 验证（浏览器实测 + 测试）

- 手机 375 默认进卡片模式：正面（apple/音标/发音钮）→ 点击翻面（MathJax H₂O 公式排版正确）→ Space 翻面 → `→` 认识（POST 成功、推进 banana、进度 1/5、清单表格行同步变绿、积分 toast 弹出）；
- RESET：confirm 对话框 → 重置后该词离开今日列表（与清单模式语义一致）；
- 模式切换：卡片↔清单双向 + localStorage 记忆；桌面默认清单、手机默认卡片；
- 滑动手势：合成 TouchEvent 右滑 → 认识推进 ✓；
- 列表：桌面 3 列/手机 1 列网格、全选、AJAX 分类切换重渲染（`?category=1` pushState）、手机底部固定批量条（勾选 2 项实测）；
- 测试 149 项：无新回归（4 失败 + 1 错误均为 main 基线存量环境问题）。

## 部署注意

- 模板/CSS/JS 变更随镜像发布；`?v=82` 已处理浏览器缓存穿透；
- 无数据迁移；旧清单模式完整保留（切换即回）。
