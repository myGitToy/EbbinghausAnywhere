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

from .models import DeepSeekUsageLog, ModelPricing, UserProfile, UserPoints
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

        billing_party = _billing_party_for(user)
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
            billing_party=billing_party,
            # local 行扣费即时完成恒 ok；study_hub 行上报后才置 ok/failed（#198）
            deduct_status=(
                DeepSeekUsageLog.DEDUCT_PENDING
                if billing_party == DeepSeekUsageLog.BILLING_PARTY_STUDY_HUB
                else DeepSeekUsageLog.DEDUCT_OK
            ),
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




def query_balance_view(user: User) -> dict:
    """GET 查询页展示用余额视图（never-raises）：联邦用户实时查门户，失败置 balance=None。"""
    hub_id = hub_user_id_of(user)
    if hub_id is None:
        return {"portal": False, "balance": ai_query_balance(user)}
    from .federated import precheck_balance

    data, _reason = precheck_balance(hub_id)
    if data is None:
        return {"portal": True, "balance": None}
    return {"portal": True, "balance": data.get("balanceCents")}


# ---------- DeepSeek 单词查询积分门槛（#197 先行修复：零门槛资损缺口） ----------

AI_QUERY_COST_POINTS = 1  # 按次固定 1 积分（本地整数账户无货币语义；复习打卡 1 次 ≈ 查询 1 次）


def ai_query_balance(user: User) -> int:
    """用户当前可用积分（无账户 = 0）。never-raises 契约。"""
    try:
        account = UserPoints.objects.filter(user=user).first()
        return account.current_points if account else 0
    except Exception:
        logger.exception("查询积分余额失败: user=%s", user)
        return 0


def charge_ai_query(user: User, reference_id: str | None = None) -> tuple[bool, str | None]:
    """DeepSeek 查询扣费单一接缝（#197 先行）：本期所有用户（含 SSO 影子号）统一本地积分，1 分/次。

    调用方契约：预检（ai_query_balance ≥ 1，不足则不发起 API 调用）→ API 调用 → 成功后调用本函数扣费；
    API 失败不调本函数 = 不扣。PointHistory reason=「DeepSeek 单词查询」，reference_id 关联 DeepSeekUsageLog.id。

    #198 积分联邦化落地后：hub_profile.study_hub_user_id 非空用户在此分流为门户代扣，本地用户维持本机制。

    返回 (ok, reason)：reason 非空 = 拒绝扣费（余额不足等），调用方据此拒绝返回查询结果。
    """
    try:
        account = UserPoints.objects.filter(user=user).first()
        if account is None or account.current_points < AI_QUERY_COST_POINTS:
            return False, "积分不足，完成复习打卡可赚积分"
        account.spend_points(AI_QUERY_COST_POINTS, reason="DeepSeek 单词查询", reference_id=reference_id)
        return True, None
    except ValueError:
        # 并发窗口下余额被花掉：spend_points 抛 Insufficient points——按拒绝处理（宁可少答一次不漏扣）
        return False, "积分不足，完成复习打卡可赚积分"
    except Exception:
        logger.exception("DeepSeek 查询扣费失败: user=%s", user)
        return False, "积分扣减失败，请稍后重试"


# ---------- DeepSeek 查询计费分流（#198 积分联邦化：SSO 绑定用户切门户代扣） ----------

FEDERATED_UNAVAILABLE_MESSAGE = "门户暂时不可达，请稍后重试"
FEDERATED_INSUFFICIENT_MESSAGE = "门户积分不足，请到 study-hub 门户领取每周配额或找家长充值"


def hub_user_id_of(user: User) -> str | None:
    """SSO 绑定的门户 userId（未绑定/查询失败 → None）。never-raises 契约。"""
    if user is None or not getattr(user, "pk", None):
        return None
    try:
        profile = UserProfile.objects.filter(user=user).only("study_hub_user_id").first()
        if profile is None:
            return None
        return profile.study_hub_user_id or None
    except Exception:
        logger.exception("查询 SSO 绑定失败: user=%s", user)
        return None


def _billing_party_for(user: User | None) -> str:
    """用量流水承担方：SSO 绑定用户 → 门户代扣；其余（本地用户/后台无主调用）→ local。"""
    return (
        DeepSeekUsageLog.BILLING_PARTY_STUDY_HUB
        if hub_user_id_of(user) is not None
        else DeepSeekUsageLog.BILLING_PARTY_LOCAL
    )


def precheck_ai_query(user: User) -> tuple[bool, str | None, dict]:
    """查询前余额门槛统一接缝（#198 分流；调用方据此决定是否发起 API 调用）。

    - 联邦用户（study_hub_user_id 非空）：门户预检，reason 非空一律拒绝（fail-closed，Q1）
    - 本地用户：本地余额 ≥ AI_QUERY_COST_POINTS（#197 原语义零变化）
    返回 (ok, reason, balance_view)；balance_view = {'portal': bool, 'balance': int|None}，
    balance 为 None 表示门户余额暂不可知（视图侧展示「暂不可达」）。
    """
    hub_id = hub_user_id_of(user)
    if hub_id is None:
        balance = ai_query_balance(user)
        if balance < AI_QUERY_COST_POINTS:
            return False, "积分不足，完成复习打卡可赚积分", {"portal": False, "balance": balance}
        return True, None, {"portal": False, "balance": balance}

    from .federated import precheck_balance  # 局部导入避免环（federated 不 import billing）

    data, reason = precheck_balance(hub_id)
    if reason is not None:
        return False, FEDERATED_UNAVAILABLE_MESSAGE, {"portal": True, "balance": None}
    balance_cents = data.get("balanceCents")
    if not data.get("canSpend"):
        return False, FEDERATED_INSUFFICIENT_MESSAGE, {"portal": True, "balance": balance_cents}
    return True, None, {"portal": True, "balance": balance_cents}


def settle_federated_ai_query(user: User, usage_log_id: int | None) -> tuple[bool, str | None, dict | None]:
    """联邦用户查询成功后的门户代扣上报（查询结果已产生，本函数不再拒绝交付）。

    - 上报成功 → 流水标 ok + 回写门户流水 id（人工兜底对账锚点）
    - 明确拒绝（密钥/未配价，重试无意义）→ 标 failed 记日志人工兜底
    - 网络失败 → 保持 pending 记日志人工兜底（不自动无限重试）
    返回 (reported, reason, balance_view)；balance_view 仅上报成功时带回门户扣后余额。
    """
    try:
        log = DeepSeekUsageLog.objects.filter(id=usage_log_id).first() if usage_log_id else None
        if log is None:
            logger.warning("门户代扣跳过：本次调用无用量流水（计费埋点失败）user=%s", user)
            return False, "用量流水缺失，门户代扣跳过", None
        hub_id = hub_user_id_of(user)
        if hub_id is None:
            return False, "用户未绑定门户，跳过代扣", None

        from .federated import report_deduction

        data, reason = report_deduction(hub_id, log)
        if reason is None:
            log.deduct_status = DeepSeekUsageLog.DEDUCT_OK
            log.remote_ledger_id = data.get("pointsLedgerId") or data.get("usageLedgerId")
            log.save(update_fields=["deduct_status", "remote_ledger_id"])
            return True, None, {"portal": True, "balance": data.get("balanceAfter")}
        if reason in ("rejected", "invalid"):
            log.deduct_status = DeepSeekUsageLog.DEDUCT_FAILED
            log.save(update_fields=["deduct_status"])
            logger.error("门户代扣被拒绝（人工兜底）: log=%s reason=%s user=%s", log.id, reason, user)
        else:
            logger.error("门户代扣上报失败，流水保持 pending（人工兜底）: log=%s reason=%s user=%s", log.id, reason, user)
        return False, FEDERATED_UNAVAILABLE_MESSAGE, None
    except Exception:
        logger.exception("门户代扣上报异常（不影响查询结果交付）: user=%s log=%s", user, usage_log_id)
        return False, FEDERATED_UNAVAILABLE_MESSAGE, None
