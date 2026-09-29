# study-hub 门户 OTT 桥接核心（Phase 5.3；ADR-0003 协议）。
# 视图在 views.py（sso_bridge / sso_logout）；本模块纯函数便于单测。

import os

import requests

DEFAULT_STUDY_HUB_URL = 'http://192.168.1.155:8090'


def study_hub_base() -> str:
    return os.environ.get('STUDY_HUB_URL', DEFAULT_STUDY_HUB_URL).rstrip('/')


def study_hub_secret() -> str:
    return os.environ.get('STUDY_HUB_APP_SECRET', '')


def consume_ott(ott):
    """用一次性令牌向 study-hub auth 换用户身份。

    返回 (payload, reason)：成功时 payload 为 {'userId', 'username'}、reason 为 None；
    失败时 payload 为 None、reason ∈ unconfigured / invalid / rejected / unreachable。
    """
    secret = study_hub_secret()
    if not secret:
        return None, 'unconfigured'
    if not isinstance(ott, str) or not (20 <= len(ott) <= 128):
        return None, 'invalid'
    try:
        resp = requests.post(
            f'{study_hub_base()}/api/ott/consume',
            json={'ott': ott, 'appSecret': secret},
            timeout=5,
        )
    except requests.RequestException:
        return None, 'unreachable'
    if resp.status_code in (401, 403):
        return None, 'rejected'
    if resp.status_code not in (200, 201):
        return None, 'invalid'
    try:
        data = resp.json()
    except ValueError:
        return None, 'invalid'
    if (not isinstance(data, dict)
            or not isinstance(data.get('userId'), str)
            or not isinstance(data.get('username'), str)):
        return None, 'invalid'
    return data, None
