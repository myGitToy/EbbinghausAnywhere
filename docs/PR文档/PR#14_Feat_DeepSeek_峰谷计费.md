# DeepSeek API 峰谷分时计费

> **项目地址**：[EbbinghausAnywhere - GitHub](https://github.com/myGitToy/EbbinghausAnywhere)
> **PR编号**：PR #14
> **创建日期**：2026-08-18
> **功能分支**：feat_DeepSeek_峰谷计费
> **目标分支**：main
> **状态**：开发中

## 功能概述

依据《DeepSeek_API_峰谷定价适配指南》（2026-08-17 生效），为项目从零搭建 DeepSeek API 计量计费基础设施：峰谷分时价格表（数据库）、每次 API 调用的用量流水落库（tokens / 档位 / 单价快照 / 费用）、admin 后台管理与前端费用展示。

在此之前，`call_deepseek_api` 只读取 `choices[0].message.content`，`response.usage` 中的 token 消耗被直接丢弃，系统没有任何价格数据与费用记录（V4 升级指南检查清单中的"更新定价计算逻辑"一项一直未实现）。

## 背景说明

DeepSeek 于北京时间 **2026-08-17 00:00** 起实施峰谷（分时）定价：

- **高峰时段**：北京时间 **[9:00, 12:00) ∪ [14:00, 18:00)**，每天适用（官方不区分工作日/周末）
- **高峰价格 = 空闲价格 × 2**，且**闲时价相比旧价也上涨**（如 v4-pro 输出价 6 → 13.5 元/百万 tokens）
- 输入 token 中缓存命中的部分单独按缓存价计费，`prompt_tokens` 已含缓存部分，公式必须相减防重复

| 模型 | 时段 | 缓存命中 | 未命中 | 输出（元/百万 tokens） |
|------|------|---------|--------|--------|
| deepseek-v4-flash | 空闲 | 0.05 | 1.5 | 4.5 |
| deepseek-v4-flash | 高峰 | 0.10 | 3.0 | 9.0 |
| deepseek-v4-pro | 空闲 | 0.15 | 4.5 | 13.5 |
| deepseek-v4-pro | 高峰 | 0.30 | 9.0 | 27.0 |

旧名 `deepseek-chat` / `deepseek-reasoner` 已弃用，价格跟 v4-flash 走（运行时归一）。

## 技术实现

### 1. 架构设计：纯逻辑与 ORM 分层

```
┌──────────────────────────────────────────────────────┐
│  EAW/pricing.py（纯逻辑，无 ORM 依赖，可独立单测）      │
│  - is_peak_time / resolve_band：峰谷时段判定            │
│  - normalize_model_name：旧模型名归一（chat/reasoner）  │
│  - PriceTier(frozen)：一档三元价格                     │
│  - resolve_tier：定档 + 峰时未配置回退闲价             │
│  - calculate_cost：缓存分段计费公式                    │
└────────────────────┬─────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────────────┐
│  EAW/billing.py（ORM 层，never-raises 契约）           │
│  - extract_usage：从 SDK 响应提取 tokens（防 MagicMock）│
│  - record_usage：查价→定档→算费→落流水（单价快照）      │
│  - get_pricing_table / get_cost_summary：展示上下文    │
└────────────────────┬─────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────────────┐
│  EAW/deepseek.py（埋点）                               │
│  call_deepseek_api：create() 返回后读 usage 落流水，    │
│  result["_usage"] 带出费用信息；双层异常保护            │
└──────────────────────────────────────────────────────┘
```

### 2. 峰谷时段判定（时区陷阱）

高峰定义锚定**北京时间**，用 `zoneinfo` 显式转换，不依赖服务器本地时区；窗口为左闭右开半开区间（9:00/14:00 整属于高峰，12:00/18:00 整已离开）：

```python
SHANGHAI = ZoneInfo("Asia/Shanghai")
PEAK_WINDOWS = ((time(9, 0), time(12, 0)), (time(14, 0), time(18, 0)))

def is_peak_time(now: datetime) -> bool:
    if now.tzinfo is None:          # 裸 datetime 按北京时间解释
        now = now.replace(tzinfo=SHANGHAI)
    moment = now.astimezone(SHANGHAI).time()
    return any(start <= moment < end for start, end in PEAK_WINDOWS)
```

> Windows 无系统 IANA 时区库，`zoneinfo` 依赖 pip 包 `tzdata`——已在 `requirements.txt` 显式声明（此前为隐性传递依赖，重建环境会失败）。

### 3. 计费公式与精度分层

```
费用 = (prompt_tokens - cache_hit_tokens) × 未命中价
     + cache_hit_tokens × 缓存命中价
     + output_tokens × 输出价          （再除以 1,000,000）
```

精度按层分离（用户确认的决议）：

| 层 | 精度 | 示例 |
|----|------|------|
| 存储·单价 | DecimalField(8, 4) | 0.0500 |
| 存储·费用 | DecimalField(14, 10)——4位价格×整数tokens÷1e6 恰好10位，**数学精确无舍入** | 0.0018200000 |
| 展示·单价 | 2 位去尾零 | "闲 1.5 / 峰 3" |
| 展示·费用 | 4 位小数 | ¥0.0018 |

`cached_tokens > prompt_tokens` 时 `max(..., 0)` 钳制，杜绝负数计费。

### 4. 数据库变更（迁移 0015）

**`ModelPricing`**（方案A变体平铺列，每模型一行）：

- 闲时三列 + 峰时三列（元/百万 tokens）——峰时三列全 > 0 才启用峰时计费，否则任何时段按闲时列计
- `pricing_updated_at` + `price_source`：官方调价留痕，admin 改价自动刷新时间戳
- 种子数据：flash / pro 两行新价格（`update_or_create` 幂等；逆向 noop 不删价格行，防止回滚再前进吞掉管理员改价）

**`DeepSeekUsageLog`**（只写不改、不清理的审计流水）：

- tokens 三列（带 `MinValueValidator(0)`）+ 档位 + **实付单价快照三列** + 费用
- `band` 记录计费时刻的**真实时段**——即使峰时价未配置回退闲价，历史账单也可解释
- `user` 可空（后台批量翻译无用户上下文，`SET_NULL`）
- 索引：`billed_at`、`(model, band)`

### 5. 埋点数据流

单点埋点在 `call_deepseek_api` 内、`create()` 返回之后、**content 解析之前**——JSON 解析失败也算消耗，流水照记（口径 = 消耗量，不是业务成功率）：

- 计费时刻口径：**响应完成时刻**判定峰/闲档（非流式调用跨整点最多差一个档位，指南 §6.2 允许）
- `extract_usage` 对 `usage=None` / 字段非 int（现有 MagicMock 测试）/ 负数全部防御跳过
- `record_usage` never-raises：整体 try/except 记日志返回 None；deepseek.py 外层再兜底——**计费失败绝不影响翻译主流程**
- 费用信息经 `result["_usage"]` 键带出（两个调用方只读白名单键，不会误存）；查询视图以不可变方式剥离后并入 JSON 响应

### 6. admin 与前端

- **ModelPricingAdmin**：可编辑，fieldsets 分组（模型/闲时价/峰时价/元数据），`save_model` 自动刷新 `pricing_updated_at`，列表以"闲 x / 峰 y"两档格式展示
- **DeepSeekUsageLogAdmin**：只读（不可增删改），按档位/模型/日期筛选，普通用户仅见自己的流水
- **查询页**：结果区显示峰（红）/闲（绿）徽标 + 本次费用（4 位小数）+ tokens 明细；DOM API 构造，无 innerHTML 注入面
- **配置页**：新增只读价目表卡片（两档价格 + 高峰时段说明 + 旧名计费说明）与费用汇总卡片（累计/本月费用、本月高峰占比）

## 变更文件

| 类型 | 文件 | 说明 |
|------|------|------|
| 新增 | `EAW/pricing.py` | 峰谷纯逻辑（时段/归一/定档/计费） |
| 新增 | `EAW/billing.py` | 计费 ORM 层（提取/落库/汇总） |
| 新增 | `EAW/migrations/0015_deepseek_peak_offpeak_pricing.py` | 两表 + 新价格种子 |
| 新增 | `EAW/tests/test_pricing.py` | 时段边界/时区/计费用例（30 个） |
| 新增 | `EAW/tests/test_model_pricing.py` | 种子/流水/汇总用例（22 个） |
| 新增 | `EAW/tests/test_deepseek_usage_logging.py` | 埋点/防泄漏用例（6 个） |
| 修改 | `EAW/models.py` | ModelPricing / DeepSeekUsageLog 两模型 |
| 修改 | `EAW/deepseek.py` | usage 埋点；常量上移自 pricing |
| 修改 | `EAW/views.py` | 查询响应暴露 usage；配置页价目表/汇总上下文 |
| 修改 | `EAW/admin.py` | 两模型注册 |
| 修改 | `EAW/templates/deepseek_query.html` | 费用徽标展示 |
| 修改 | `EAW/templates/deepseek_config.html` | 价目表 + 费用汇总卡片 |
| 修改 | `requirements.txt` | 显式声明 tzdata |
| 修改 | `docs/DEEPSEEK_V4_UPGRADE_GUIDE.md` | 价格表更新为峰谷新价；检查清单标记完成 |

## 测试

新增 **58 个测试用例**全部通过，覆盖《适配指南》§8 全部清单：

- **时段边界**：8/18(周二) 09:00:00 高峰 / 12:00:00 空闲 / 14:00:00 高峰 / 18:00:00 空闲（半开区间）；08:59:59、23:00 空闲
- **周末口径**：8/23(周日) 10:00 高峰（官方不区分周末）
- **时区**：UTC 01:30（=北京 09:30）高峰；裸 datetime 按北京时间解释
- **缓存分段**：prompt=1000, cached=400, output=200 闲价 flash → `0.0018200000`（10 位精确断言）；cached==prompt 时未命中费为 0；峰价恰为闲价 2 倍
- **回退审计**：峰列全 0 / 部分 0 → 按闲价计费但 `band` 仍记真实时段
- **防御**：MagicMock usage 不落库；`record_usage` 任何异常不外抛；计费抛异常时翻译结果照常返回
- **防泄漏**：`_usage` 键不出现在响应 `data` 中，保存链路不携带费用信息

全量回归 `manage.py test EAW.tests`：121 个用例，113 通过；8 个失败为**既有问题**（已用 `git stash` 暂存本次全部改动后复跑实证——签到 streak 逻辑断言与五子棋旧构建哈希 `main.dc7695ae.js`，与本次无关）。

迁移已验证：应用 → 回滚 0014 → 再前进，种子 `update_or_create` 幂等；`makemigrations --check` 无漂移。

## 后续工作

- [ ] 白天人工端到端验证（runserver → 查词看徽标/费用 → admin 看流水 → 配置页价目表）
- [ ] 官方下次调价时在 admin 直接改价（`pricing_updated_at` 自动留痕）
- [ ] 既有 8 个失败测试另行排查（五子棋测试硬编码旧构建哈希）
- [ ] V4 升级指南剩余未完成项：`reasoning_content` 处理、`DEEPSEEK_THINKING_ENABLED` 环境变量

## 参考

- 《DeepSeek_API_峰谷定价适配指南》（C:\Users\GHUIQ\repos，2026-08-16 整理）
- [DeepSeek 官方价格页](https://api-docs.deepseek.com/zh-cn/quick_start/pricing)
- [DEEPSEEK_V4_UPGRADE_GUIDE.md](../DEEPSEEK_V4_UPGRADE_GUIDE.md) §1/§6/§7 已随本 PR 同步修订
