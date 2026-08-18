# billing.py
"""
DeepSeek 计费 ORM 层：查价、落用量流水、价目表与费用汇总上下文。

对外函数一律不抛异常（never-raises 契约）：
计费/审计失败绝不影响翻译主流程，仅记日志返回 None。
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.db.models import Sum

from .models import DeepSeekUsageLog, ModelPricing
from .pricing import (
    BAND_PEAK,
    PriceTier,
    SHANGHAI,
    calculate_cost,
    normalize_model_name,
    resolve_tier,
)

logger = logging.getLogger(__name__)

ZERO = Decimal("0")


def get_pricing_for_model(model_name: str) -> ModelPricing | None:
    """
    按归一化后的模型名查价格行。

    :return: ModelPricing 实例；模型无价格行（含 None 入参）返回 None
    """
    normalized = normalize_model_name(model_name)
    if not normalized:
        return None
    try:
        return ModelPricing.objects.get(model_name=normalized)
    except ModelPricing.DoesNotExist:
        return None


def extract_usage(response) -> tuple[int, int, int] | None:
    """
    从 OpenAI SDK 响应对象提取 token 用量。

    :return: (prompt_tokens, cached_tokens, completion_tokens)；
             usage 缺失、字段非 int（如测试中的 MagicMock）、负数 → None
    """
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    prompt = getattr(usage, "prompt_tokens", None)
    output = getattr(usage, "completion_tokens", None)
    details = getattr(usage, "prompt_tokens_details", None)
    cached = getattr(details, "cached_tokens", 0) if details is not None else 0

    if not isinstance(prompt, int) or not isinstance(output, int):
        return None
    if prompt < 0 or output < 0:
        return None
    if not isinstance(cached, int) or cached < 0:
        cached = 0
    return prompt, cached, output


def record_usage(
    *,
    model: str,
    user: User | None,
    prompt_tokens: int,
    cached_tokens: int,
    output_tokens: int,
    now: datetime | None = None,
) -> DeepSeekUsageLog | None:
    """
    查价 → 定档 → 算费 → 落用量流水（含实付单价快照）。

    :param now: 计费时刻（测试注入固定时刻用）；缺省取当前时刻。
                口径：响应完成时刻判定峰/闲档（指南§6.2）。
    :return: 流水实例；模型无价格行或任何异常时返回 None（不抛出）
    """
    try:
        pricing = get_pricing_for_model(model)
        if pricing is None:
            logger.warning("未找到模型价格行，跳过计费: %r", model)
            return None

        offpeak = PriceTier(
            cache_hit_price=pricing.offpeak_cache_hit_price,
            cache_miss_price=pricing.offpeak_cache_miss_price,
            output_price=pricing.offpeak_output_price,
        )
        peak = PriceTier(
            cache_hit_price=pricing.peak_cache_hit_price,
            cache_miss_price=pricing.peak_cache_miss_price,
            output_price=pricing.peak_output_price,
        )
        band, tier = resolve_tier(offpeak, peak, now)
        cost = calculate_cost(prompt_tokens, cached_tokens, output_tokens, tier)

        return DeepSeekUsageLog.objects.create(
            user=user,
            model=normalize_model_name(model),
            band=band,
            prompt_tokens=prompt_tokens,
            cached_tokens=cached_tokens,
            output_tokens=output_tokens,
            billed_cache_hit_price=tier.cache_hit_price,
            billed_cache_miss_price=tier.cache_miss_price,
            billed_output_price=tier.output_price,
            cost=cost,
            billed_at=now or datetime.now(SHANGHAI),
        )
    except Exception:
        logger.exception("记录 DeepSeek 用量流水失败: model=%r", model)
        return None


def display_price(price: Decimal) -> str:
    """展示格式：最多 2 位小数并去尾零（1.5000 → 1.5，0.0500 → 0.05）。"""
    quantized = price.quantize(Decimal("0.01"))
    text = f"{quantized:f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def display_price_pair(offpeak_price: Decimal, peak_price: Decimal, peak_enabled: bool) -> str:
    """两档展示（指南§7）："闲 1.5 / 峰 3"；峰时未配置时只显示 "闲 1.5"。"""
    if not peak_enabled:
        return f"闲 {display_price(offpeak_price)}"
    return f"闲 {display_price(offpeak_price)} / 峰 {display_price(peak_price)}"


def get_pricing_table() -> list[dict]:
    """
    配置页价目表上下文：每模型一行，两档价格展示字符串 + 峰时启用标记。
    """
    rows = []
    for pricing in ModelPricing.objects.all().order_by("model_name"):
        peak_enabled = pricing.peak_enabled
        rows.append({
            "model": pricing.model_name,
            "cache_hit": display_price_pair(
                pricing.offpeak_cache_hit_price, pricing.peak_cache_hit_price, peak_enabled
            ),
            "cache_miss": display_price_pair(
                pricing.offpeak_cache_miss_price, pricing.peak_cache_miss_price, peak_enabled
            ),
            "output": display_price_pair(
                pricing.offpeak_output_price, pricing.peak_output_price, peak_enabled
            ),
            "peak_enabled": peak_enabled,
            "updated_at": pricing.pricing_updated_at,
        })
    return rows


def get_cost_summary(now: datetime | None = None) -> dict:
    """
    轻量费用汇总：累计费用、本月费用（北京自然月）、本月高峰费用与占比。

    :param now: 统计基准时刻（测试注入）；缺省取当前北京时间。
    :return: {total_cost, month_cost, month_peak_cost, peak_ratio}；
             peak_ratio 为 None 表示本月无费用（避免除零）
    """
    empty = {
        "total_cost": ZERO,
        "month_cost": ZERO,
        "month_peak_cost": ZERO,
        "peak_ratio": None,
    }
    try:
        now = now or datetime.now(SHANGHAI)
        if now.tzinfo is None:
            now = now.replace(tzinfo=SHANGHAI)
        month_start = now.astimezone(SHANGHAI).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        total_cost = (
            DeepSeekUsageLog.objects.aggregate(total=Sum("cost"))["total"] or ZERO
        )
        month_logs = DeepSeekUsageLog.objects.filter(billed_at__gte=month_start)
        month_cost = month_logs.aggregate(total=Sum("cost"))["total"] or ZERO
        month_peak_cost = (
            month_logs.filter(band=BAND_PEAK).aggregate(total=Sum("cost"))["total"] or ZERO
        )

        peak_ratio = None
        if month_cost > 0:
            ratio = (month_peak_cost / month_cost * 100).quantize(Decimal("0.1"))
            peak_ratio = f"{ratio:f}%"

        return {
            "total_cost": total_cost,
            "month_cost": month_cost,
            "month_peak_cost": month_peak_cost,
            "peak_ratio": peak_ratio,
        }
    except Exception:
        logger.exception("统计 DeepSeek 费用汇总失败")
        return empty
