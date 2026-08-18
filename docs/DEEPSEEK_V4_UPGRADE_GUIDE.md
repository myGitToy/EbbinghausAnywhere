# DeepSeek V4 API 升级指南

> 适用于 DeepSeek API 从 V3.x (deepseek-chat/deepseek-reasoner) 升级到 V4 (deepseek-v4-flash/deepseek-v4-pro) 的场景。其他项目可参考本文档进行升级。

## 1. V4 模型概览

| 属性 | deepseek-v4-flash | deepseek-v4-pro |
|------|-------------------|-----------------|
| **定位** | 快速响应，通用对话 | 深度推理，复杂任务 |
| **Base URL** | `https://api.deepseek.com` | `https://api.deepseek.com` |
| **Anthropic 格式** | `https://api.deepseek.com/anthropic` | `https://api.deepseek.com/anthropic` |
| **上下文长度** | 1M tokens | 1M tokens |
| **最大输出** | 384K tokens | 384K tokens |
| **思考模式** | 支持开关（默认开启） | 支持开关（默认开启） |
| **输入价格（缓存命中）** | ¥0.05 空闲 / ¥0.10 高峰 | ¥0.15 空闲 / ¥0.30 高峰 |
| **输入价格（缓存未命中）** | ¥1.5 空闲 / ¥3.0 高峰 | ¥4.5 空闲 / ¥9.0 高峰 |
| **输出价格** | ¥4.5 空闲 / ¥9.0 高峰 | ¥13.5 空闲 / ¥27.0 高峰 |

> **峰谷分时定价（2026-08-17 起生效）**：高峰时段为北京时间 9:00–12:00、14:00–18:00（每天适用，官方不区分周末），高峰价格为空闲的 2 倍。单位：元/百万 tokens。本项目的计费实现见 `EAW/pricing.py`（时段判定与计费公式）、`EAW/billing.py`（用量流水）与 `ModelPricing` 价格表（admin 可改价留痕）。

### 旧模型名称映射（向后兼容）

DeepSeek API 内部自动映射：
- `deepseek-chat` → `deepseek-v4-flash`（非思考模式）
- `deepseek-reasoner` → `deepseek-v4-flash`（思考模式）

> 旧名称仍可调用，但建议迁移到新名称。

## 2. 思考模式 API 用法

### 2.1 开关控制

思考模式默认**开启**。通过 `thinking` 参数控制：

```python
# 开启思考模式
response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=messages,
    reasoning_effort="high",
    extra_body={"thinking": {"type": "enabled"}},
)

# 关闭思考模式
response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=messages,
    temperature=0.7,
    frequency_penalty=0.5,
    extra_body={"thinking": {"type": "disabled"}},
)
```

### 2.2 推理强度控制

| 参数值 | 效果 |
|--------|------|
| `high` | 平衡速度与质量（默认） |
| `max` | 最大推理深度，适合复杂 Agent 任务 |

> `low`/`medium` 映射为 `high`，`xhigh` 映射为 `max`。

### 2.3 Anthropic 格式

```python
# Anthropic 格式控制参数
{
    "output_config": {
        "effort": "high"  # 或 "max"
    }
}
```

## 3. 参数兼容性矩阵

| 参数 | 非思考模式 | 思考模式 |
|------|-----------|---------|
| `temperature` | 生效 | **无效**（不报错但忽略） |
| `top_p` | 生效 | **无效** |
| `presence_penalty` | 生效 | **无效** |
| `frequency_penalty` | 生效 | **无效** |
| `max_tokens` | 生效 | 生效 |
| `reasoning_effort` | 不适用 | 生效 |
| `extra_body.thinking` | 生效 | 生效 |
| `tools` (Tool Calls) | 生效 | 生效 |
| `response_format` (JSON) | 生效 | 生效 |

> **重要**：思考模式下设置 `temperature` 等参数不会报错，但也不会生效。为避免混淆，建议在代码中显式排除。

## 4. 响应处理

思考模式下，响应包含 `reasoning_content`（思维链）和 `content`（最终回答）：

```python
# 非流式
response = client.chat.completions.create(...)
msg = response.choices[0].message
reasoning = msg.reasoning_content  # 思维链内容
content = msg.content              # 最终回答

# 流式
for chunk in response:
    if chunk.choices[0].delta.reasoning_content:
        reasoning += chunk.choices[0].delta.reasoning_content
    else:
        content += chunk.choices[0].delta.content
```

### 多轮对话注意事项

- **无工具调用**时：中间轮次的 `reasoning_content` 无需回传，API 会忽略
- **有工具调用**时：`reasoning_content` **必须回传**，否则返回 400 错误

```python
# 推荐做法：直接 append 完整 message 对象
messages.append(response.choices[0].message)
```

## 5. 代码示例

### 5.1 OpenAI SDK（推荐）

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-api-key",
    base_url="https://api.deepseek.com",
)

messages = [{"role": "user", "content": "你的问题"}]

# 思考模式
response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=messages,
    reasoning_effort="high",
    extra_body={"thinking": {"type": "enabled"}},
)
print(response.choices[0].message.content)

# 非思考模式
response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=messages,
    temperature=0.7,
    max_tokens=4096,
    extra_body={"thinking": {"type": "disabled"}},
)
print(response.choices[0].message.content)
```

### 5.2 条件参数构建（思考模式兼容）

```python
def build_api_kwargs(model, messages, thinking_enabled=True,
                     reasoning_effort="high", temperature=0.7,
                     frequency_penalty=0.5, max_tokens=4096):
    """根据思考模式状态构建API参数"""
    kwargs = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if thinking_enabled:
        kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
        kwargs["reasoning_effort"] = reasoning_effort
    else:
        kwargs["temperature"] = temperature
        kwargs["frequency_penalty"] = frequency_penalty
    return kwargs

# 使用
api_kwargs = build_api_kwargs(
    model="deepseek-v4-flash",
    messages=messages,
    thinking_enabled=True,
    reasoning_effort="high",
)
response = client.chat.completions.create(**api_kwargs)
```

### 5.3 工具调用（思考模式）

```python
tools = [{"type": "function", "function": {"name": "get_weather", ...}}]

response = client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=messages,
    tools=tools,
    reasoning_effort="high",
    extra_body={"thinking": {"type": "enabled"}},
)

# 注意：工具调用轮次的 reasoning_content 必须在后续请求中回传
messages.append(response.choices[0].message)
```

## 6. 定价对比（旧 vs 新）

> ⚠️ **历史价格表**：下表为 V4 上线时（2026-02）的价格。官方已于 **2026-08-17** 实施峰谷分时定价且闲时价也上调，当前生效价格见本文 §1 与 `ModelPricing` 价格表。

| 项目 | deepseek-chat (旧) | deepseek-v4-flash（V4 上线时） | deepseek-v4-pro（V4 上线时） |
|------|--------------------|-----------------------|---------------------|
| 输入（缓存命中） | ¥0.2 | ¥0.2 | ¥1 |
| 输入（缓存未命中） | ¥2 | **¥1**（降低50%） | ¥12 |
| 输出 | ¥3 | **¥2**（降低33%） | ¥24 |
| 上下文 | 128K | **1M**（8倍） | **1M**（8倍） |
| 最大输出 | 8K | **384K**（48倍） | **384K**（6倍） |

> v4-flash 相比旧版 chat 模型：**更便宜、更强**。

## 7. 迁移检查清单

- [ ] 模型名称：`deepseek-chat` → `deepseek-v4-flash`，`deepseek-reasoner` → `deepseek-v4-pro`
- [ ] 添加思考模式控制：`extra_body={"thinking": {"type": "enabled/disabled"}}`
- [ ] 添加推理强度：`reasoning_effort="high"` 或 `"max"`
- [ ] 思考模式下**排除** `temperature`/`top_p`/`presence_penalty`/`frequency_penalty`
- [ ] 更新 `max_tokens` 上限（从 8K 提升至 384K）
- [x] 更新定价计算逻辑（`EAW/pricing.py` 峰谷时段判定 + 缓存分段计费、`EAW/billing.py` 用量流水、`ModelPricing` 价格表迁移 0015，支持 2026-08-17 峰谷新价体系）
- [ ] 处理响应中的 `reasoning_content` 字段（多轮对话需回传）
- [ ] 更新配置文件和环境变量
- [ ] 更新 UI 下拉框和模型选择器
- [ ] 更新 `.env` 文件添加 `DEEPSEEK_THINKING_ENABLED` 和 `DEEPSEEK_REASONING_EFFORT`

## 8. 参考资料

- [DeepSeek 官方文档 - 模型与价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing)
- [DeepSeek 官方文档 - 思考模式](https://api-docs.deepseek.com/zh-cn/guides/thinking_mode)
