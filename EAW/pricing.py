# pricing.py
"""
DeepSeek 峰谷定价纯逻辑（无 Django ORM 依赖，可独立单测）

价格单位：元/百万 tokens。
依据：《DeepSeek_API_峰谷定价适配指南》（2026-08-17 生效）：
- 高峰时段为北京时间 [9:00, 12:00) ∪ [14:00, 18:00)，每天适用（官方不区分周末）
- 高峰价格 = 空闲价格 × 2；计费公式见 calculate_cost
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")

# 高峰窗口，左闭右开半开区间：9:00/14:00 整属于高峰，12:00/18:00 整已离开
PEAK_WINDOWS: tuple[tuple[time, time], ...] = (
    (time(9, 0), time(12, 0)),
    (time(14, 0), time(18, 0)),
)

BAND_PEAK = "peak"
BAND_OFFPEAK = "offpeak"

DEFAULT_MODEL = "deepseek-v4-flash"
# 旧模型名已弃用，价格跟 v4-flash 走（指南§2）
LEGACY_MODEL_MAP: dict[str, str] = {
    "deepseek-chat": DEFAULT_MODEL,
    "deepseek-reasoner": DEFAULT_MODEL,
}

# 费用量化精度：4 位小数价格 × 整数 tokens ÷ 1e6 恰好 10 位小数，无舍入损失
COST_QUANTUM = Decimal("0.0000000001")
MILLION = Decimal(1_000_000)


@dataclass(frozen=True)
class PriceTier:
    """一档三元价格（元/百万 tokens）。"""

    cache_hit_price: Decimal
    cache_miss_price: Decimal
    output_price: Decimal

    @property
    def is_configured(self) -> bool:
        """三价均 > 0 才视为已配置；任何一列 ≤ 0 视为整档未配置（峰时回退判定用）。"""
        return all(
            price > 0
            for price in (self.cache_hit_price, self.cache_miss_price, self.output_price)
        )


def is_peak_time(now: datetime) -> bool:
    """
    判定是否处于高峰时段。

    :param now: 任意时区的 aware datetime（换算到北京时间后判定），
                或裸 datetime（按北京时间解释）
    """
    if now.tzinfo is None:
        now = now.replace(tzinfo=SHANGHAI)
    moment = now.astimezone(SHANGHAI).time()
    return any(start <= moment < end for start, end in PEAK_WINDOWS)


def resolve_band(now: datetime | None = None) -> str:
    """
    返回 'peak' 或 'offpeak'。

    :param now: 判定时刻，缺省取当前北京时间。
                计费口径：以响应完成时刻为准（指南§6.2），跨整点最多差一个档位。
    """
    if now is None:
        now = datetime.now(SHANGHAI)
    return BAND_PEAK if is_peak_time(now) else BAND_OFFPEAK


def normalize_model_name(raw: str) -> str:
    """旧模型名归一到 v4 规范名（chat/reasoner → flash），未知名原样返回。"""
    return LEGACY_MODEL_MAP.get(raw, raw)


def resolve_tier(
    offpeak: PriceTier,
    peak: PriceTier,
    now: datetime | None = None,
) -> tuple[str, PriceTier]:
    """
    返回 (真实时段 band, 实际计费用的 PriceTier)。

    band 始终记录真实时段；仅当 band 为 peak 且 peak 档已配置（三价均 > 0）
    时使用峰价，否则（含峰时列未配置的回退场景）使用闲价——
    流水快照记录实付单价，官方调价后历史账单才可解释（指南§6.3）。
    """
    band = resolve_band(now)
    if band == BAND_PEAK and peak.is_configured:
        return band, peak
    return band, offpeak


def calculate_cost(
    prompt_tokens: int,
    cached_tokens: int,
    output_tokens: int,
    tier: PriceTier,
) -> Decimal:
    """
    计算单次调用费用（元）。

    prompt_tokens 已包含缓存命中部分，未命中部分必须相减，防止重复计费：
    费用 = (prompt - cached) × 未命中价 + cached × 命中价 + output × 输出价，
    单价为元/百万 tokens，故再除以 1e6。结果量化到 10 位小数（数学精确）。
    """
    cache_miss_tokens = max(prompt_tokens - cached_tokens, 0)
    total = (
        Decimal(cache_miss_tokens) * tier.cache_miss_price
        + Decimal(cached_tokens) * tier.cache_hit_price
        + Decimal(output_tokens) * tier.output_price
    )
    return (total / MILLION).quantize(COST_QUANTUM)
