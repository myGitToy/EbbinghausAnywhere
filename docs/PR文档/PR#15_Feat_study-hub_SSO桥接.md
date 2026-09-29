# PR #15 · study-hub 门户 SSO 桥接 + CORS 收紧

- 日期：2026-09-30 ｜ 状态：已合并
- 关联：study-hub 仓库 issue #37/#39（Phase 5.2/5.3）、ADR-0003（OTT 一次性令牌 SSO）

## 改动

1. **`/sso/bridge/` 换票入口**（`EAW/sso.py` + `views.sso_bridge` + urls）：门户携 `?ott=` 跳入 → 服务间调 study-hub auth `/api/ott/consume` 换身份 → 匹配/建**影子用户**（`set_unusable_password` 占位，本地账密体系不受影响）→ `django login()` 建会话 → 跳首页；失败跳登录页带 `?sso=<reason>`。环境变量：`STUDY_HUB_URL`（默认 `http://192.168.1.155:8090`）、`STUDY_HUB_APP_SECRET`（未配置即 SSO 未启用，保留独立可用性）。
2. **`/sso/logout/` 服务间全局登出**（Phase 5.4 预置）：POST `{appSecret, username}` → 删除该用户全部 Django 会话。
3. **CORS 收紧**：`CORS_ALLOW_ALL_ORIGINS=True`（两处定义）→ `False` + `CORS_ALLOWED_ORIGINS` 门户白名单（192.168.1.155:8092 等）；`CSRF_TRUSTED_ORIGINS` 补门户 origin。

## 验证

- 新增 `EAW/tests/test_sso_bridge.py` 9 用例全绿（换票/影子用户/失败四分支/服务间登出/CORS 断言）；
- 与 study-hub 隔离实例真实联调全绿：OTT 签发→bridge 302+sessionid→`/list/` 登录态 200（无 cookie 对照 302）→影子用户 unusable password→重放 rejected→CORS 预检白名单放行/陌生 origin 拒绝；
- 全量测试 131 项：改动后 9 失败 vs **基线（stash 后）21 失败**——存量 flaky（两轮数字漂移），与本次改动无关，新测试无回归。

## 部署注意

- 容器环境需注入 `STUDY_HUB_URL`/`STUDY_HUB_APP_SECRET`（secret 与 study-hub 侧 `EWA_APP_SECRET` 同值，见其 `data/FEDERATED-APPS.txt`）；
- CORS 已收紧：如有其他前端跨域调用本站 API，需将其 origin 加入白名单。
