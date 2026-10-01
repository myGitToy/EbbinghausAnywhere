# PR #15 · SSO 账号对齐 #510 状态机：证明式绑定（UserProfile/绑定票/绑定页）

- 日期：2026-10-01 ｜ 状态：已开 PR #15
- 关联：study-hub 仓库 issue #80（本 PR 的 issue）、ADR-0015（联邦账号对齐状态机，随本批提交到 study-hub）、airlinesim 仓库 #510（语义源）、本仓库 PR#15（前置交付）

## 背景（为什么改）

PR#15 的 bridge 按 `username` 匹配/建影子用户，两处缺陷（study-hub #80，2026-10-01 三轮拷问定稿）：

1. **同名冒领**：门户用户换票会直接登入本地同名真实账号（门户侧开放注册，按名合并 = 同名接管漏洞）；
2. **失败静默**：换票失败 302 到登录页带 `?sso=<reason>`，但模板不渲染，用户只看到"莫名回到登录页"。

联邦三成员（airlinesim / cube-wall / EAW）账号语义需一致，对齐目标是 airlinesim #510 的**证明式绑定**状态机。

## 改动

1. **`UserProfile` 链接表**（`EAW/models.py` + 迁移 0016）：`OneToOne(User)` + `study_hub_user_id`（唯一）；注册 Django admin（极端情况手工兜底）。
2. **`sso_bridge` 三分支状态机**（`EAW/views.py`）：
   - 已绑定该 userId → **直登**（门户改名同步本地用户名，数据不断链）；
   - 未绑定 + 本地同名 → **冲突**：签 10 分钟绑定票，302 绑定页，**绝不按名自动合并**；
   - 未绑定 + 无同名 → **建影子号**（`create_user` 无密码 = 不可用密码）+ 即建即绑 + 默认数据初始化。
3. **绑定票**（`EAW/sso.py`）：`TimestampSigner` + 专用 salt `sso-bind`、TTL 600s、不落库——语义等价 airlinesim 的 purpose JWT；`load_bind_ticket` 返回 `invalid/expired` 失败原因。
4. **`/sso/bind/` 绑定页**（视图 + `templates/sso_bind.html`）：
   - `mode=bind`：验**本地账号密码**证明归属 → 绑定 → 登录（本地密码保留，混合登录可用）；
   - `mode=rename`：换用户名新建影子号（Django 用户名口径校验 + 唯一性）→ 绑定 → 登录；
   - 票过期/篡改 → 跳登录页 `?sso=bind_<reason>`；**抢先绑定竞态** → 直接登录已绑定账号。
5. **`_provision_new_user` 助手**：本地注册与 SSO 影子号共用初始化（Public 组 / `is_staff` / 默认"单词"分类 / 复习曲线）——修复 PR#15 影子号无默认数据、进站即空白的缺口。
6. **`/sso/logout/` 兼容可选 `userId`**（有则按绑定表优先，无则按 username）——中心侧暂未发送，向前兼容（ADR-0015 要求）。
7. **登录页 `?sso=` 中文提示**（`custom_login` + `login.html`）：unconfigured/invalid/rejected/unreachable/bind_invalid/bind_expired 六种原因不再静默。
8. **`ALLOWED_HOSTS` 环境变量化**（`env.list('ALLOWED_HOSTS', default=['*'])`）：开发默认不变，部署收紧为 `192.168.1.155,localhost`（#72 上线项）。

## 验证

- `EAW/tests/test_sso_bridge.py` 重写为 23 用例全绿：三分支到达（直登+改名同步/建影子+默认数据/同名冲突不出会话）、绑定页（验密对错两路/已绑他人拒绝/换名对错两路）、票篡改与过期、抢先绑定竞态、logout userId 优先与 username 回退、`?sso=` 文案、CORS 白名单断言；
- 全量 145 测试：4 失败 + 1 错误均为**存量环境问题**（缺 `.env`、gobang 静态构建产物、`test_review_scenario` 导入依赖 local_settings），已在干净 worktree 的 main 基线上复现同样失败，与本 PR 无关。

## 部署注意

- 迁移 0016 首次部署自动执行（`entrypoint.sh` 已含 `migrate`）；
- 新端点 `/sso/bind/` 无需加入 study-hub 侧任何配置（bridgeUrl 派生 logout 的约定不变）；
- 上线时（#72）注入 `ALLOWED_HOSTS=192.168.1.155,localhost` 收紧。

## 对齐声明

本 PR 后 EAW 与 airlinesim 的 SSO 到达语义一致（ADR-0015）；cube-wall 对齐见 study-hub #89。
