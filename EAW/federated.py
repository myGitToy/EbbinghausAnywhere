# study-hub 门户积分代扣客户端（#198，与 sso.py 同层纯函数模块，never-raises）。
# 协议：POST {STUDY_HUB_POINTS_URL}/federated-points/{precheck|deduct}，appSecret 即凭证；
# 计价在门户侧（传用量不传钱），幂等键 = DeepSeekUsageLog.id（重试安全）。

import logging
import os

import requests

from .sso import study_hub_secret

logger = logging.getLogger(__name__)

# 同机直连 hub-api；生产 EAW 容器（bridge 网络）经门户 web 反代可达：
# STUDY_HUB_POINTS_URL=http://192.168.1.155:8092/hub-api
DEFAULT_STUDY_HUB_POINTS_URL = "http://127.0.0.1:8091/api"

# reason 语义与 sso.consume_ott 对齐：unconfigured / unreachable / rejected / invalid
REJECT_REASONS = ("rejected", "invalid")


def points_base() -> str:
    return os.environ.get("STUDY_HUB_POINTS_URL", DEFAULT_STUDY_HUB_POINTS_URL).rstrip("/")


def _post(path: str, payload: dict, timeout: int = 5) -> tuple[dict | None, str | None]:
    """公共 POST：返回 (data, reason)；失败时 data 为 None。"""
    secret = study_hub_secret()
    if not secret:
        return None, "unconfigured"
    try:
        resp = requests.post(f"{points_base()}/federated-points/{path}", json=payload, timeout=timeout)
    except requests.RequestException as exc:
        logger.warning("study-hub 积分端点不可达: %s", exc)
        return None, "unreachable"
    if resp.status_code in (401, 403):
        return None, "rejected"
    if resp.status_code not in (200, 201):
        logger.warning("study-hub 积分端点异常响应: %s %s", resp.status_code, resp.text[:200])
        return None, "invalid"
    try:
        data = resp.json()
    except ValueError:
        return None, "invalid"
    if not isinstance(data, dict):
        return None, "invalid"
    return data, None


def precheck_balance(hub_user_id: str) -> tuple[dict | None, str | None]:
    """门户余额预检：→ ({balanceCents, canSpend}, None) | (None, reason)。

    fail-closed 由调用方保证：reason 非空一律拒绝发起 DeepSeek 调用（#198 Q1）。
    """
    secret = study_hub_secret()
    if not secret:
        return None, "unconfigured"
    return _post("precheck", {"appSecret": secret, "userId": hub_user_id})


def report_deduction(hub_user_id: str, usage_log) -> tuple[dict | None, str | None]:
    """查询成功后上报门户代扣（幂等键 = usage_log.id，门户唯一约束下重放返回首次结果）。

    返回 (data, reason)：data 含 pointsLedgerId/usageLedgerId/balanceAfter/deducted/costCents/replayed；
    rejected/invalid = 门户明确拒绝（密钥/未配价模型，重试无意义）；unreachable = 网络失败（留 pending 人工兜底）。
    """
    secret = study_hub_secret()
    if not secret:
        return None, "unconfigured"
    occurred_at = usage_log.billed_at
    payload = {
        "appSecret": secret,
        "userId": hub_user_id,
        "jobType": "ewa_word_lookup",
        "model": usage_log.model,
        # 三向 token：prompt_tokens 含缓存命中（门户 UsageTokens 同口径，非缓存 = input - cacheHit）
        "inputTokens": usage_log.prompt_tokens,
        "cacheHitTokens": usage_log.cached_tokens,
        "outputTokens": usage_log.output_tokens,
        "band": usage_log.band,
        "occurredAt": occurred_at.isoformat() if occurred_at else None,
        "idempotencyKey": str(usage_log.id),
    }
    return _post("deduct", payload)
