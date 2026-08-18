"""
Tests for DeepSeek usage metering integration:
call_deepseek_api 埋点（读 usage 落流水 + _usage 键传出）与查询视图的费用暴露。
锁定：计费失败不影响翻译主流程、MagicMock usage 不落库、_usage 不泄漏进 data。
"""
import json
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase

from EAW.models import DeepSeekUsageLog
from EAW.pricing import BAND_PEAK, SHANGHAI

CONTENT = '{"uk_phonetic":"/a/","us_phonetic":"/a/","meaning":"test","example_sentences":[]}'
PEAK_NOW = datetime(2026, 8, 18, 10, 0, 0, tzinfo=SHANGHAI)  # 周二 10:00 → 高峰


def fixed_datetime(fixed):
    """构造 now() 恒返回 fixed 的 datetime 替身，注入 billing/pricing 两个模块。"""

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed if tz is not None else fixed.replace(tzinfo=None)

    return FixedDatetime


def make_response(prompt=1000, cached=400, output=200):
    """构造带真实类型 usage 的类 SDK 响应；prompt=None 表示无 usage。"""
    message = SimpleNamespace(message=SimpleNamespace(content=CONTENT))
    if prompt is None:
        return SimpleNamespace(usage=None, choices=[message])
    usage = SimpleNamespace(
        prompt_tokens=prompt,
        completion_tokens=output,
        prompt_tokens_details=SimpleNamespace(cached_tokens=cached),
    )
    return SimpleNamespace(usage=usage, choices=[message])


class TestUsageMeteringInCallDeepSeekApi(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="meter", password="pass")

    def _call(self, response, user=None):
        from EAW.deepseek import call_deepseek_api

        with patch("EAW.deepseek.OpenAI") as mock_openai_cls, \
                patch("EAW.deepseek.DEEPSEEK_API_KEY", "sk-test-key"):
            client = MagicMock()
            mock_openai_cls.return_value = client
            client.chat.completions.create.return_value = response
            return call_deepseek_api("apple", config=None, user=user)

    def test_usage_logged_with_peak_band_and_usage_key(self):
        with patch("EAW.billing.datetime", fixed_datetime(PEAK_NOW)), \
                patch("EAW.pricing.datetime", fixed_datetime(PEAK_NOW)):
            result = self._call(make_response(), user=self.user)

        self.assertTrue(result)
        log = DeepSeekUsageLog.objects.get()
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.model, "deepseek-v4-flash")
        self.assertEqual(log.band, BAND_PEAK)
        self.assertEqual(log.prompt_tokens, 1000)
        self.assertEqual(log.cached_tokens, 400)
        self.assertEqual(log.output_tokens, 200)
        # (600×3.0 + 400×0.1 + 200×9.0)/1e6
        self.assertEqual(log.cost, Decimal("0.0036400000"))

        self.assertEqual(result["_usage"]["band"], BAND_PEAK)
        self.assertEqual(result["_usage"]["prompt_tokens"], 1000)
        self.assertEqual(result["_usage"]["cached_tokens"], 400)
        self.assertEqual(result["_usage"]["output_tokens"], 200)

    def test_usage_missing_no_log_no_usage_key(self):
        result = self._call(make_response(prompt=None))
        self.assertTrue(result)
        self.assertNotIn("_usage", result)
        self.assertEqual(DeepSeekUsageLog.objects.count(), 0)

    def test_magicmock_usage_no_log_no_exception(self):
        """现有 v4 测试的 MagicMock 响应：usage 属性非 int → 跳过计费不落库。"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = CONTENT

        result = self._call(mock_response)
        self.assertTrue(result)
        self.assertEqual(DeepSeekUsageLog.objects.count(), 0)

    def test_billing_failure_does_not_break_translation(self):
        with patch("EAW.billing.record_usage", side_effect=RuntimeError("boom")):
            result = self._call(make_response(), user=self.user)
        # 翻译结果照常返回，仅无计费信息
        self.assertTrue(result)
        self.assertNotIn("_usage", result)


class TestQueryViewUsageExposure(TestCase):
    def test_usage_exposed_in_json_and_not_leaked_into_data(self):
        user = User.objects.create_user(username="viewer", password="pass")
        self.client.force_login(user)

        fake_result = {
            "phonetic": ["/æpl/", "/æpl/"],
            "parts_and_means": ["例句1: an apple\n翻译: 一个苹果"],
            "simple_meaning": ["简明释义: 苹果"],
            "src_tts": "",
            "_usage": {
                "band": "peak",
                "cost": "0.0036400000",
                "prompt_tokens": 1000,
                "cached_tokens": 400,
                "output_tokens": 200,
            },
        }
        with patch("EAW.views.call_deepseek_api", return_value=fake_result):
            response = self.client.post(
                "/deepseek/query/",
                data=json.dumps({"word": "apple"}),
                content_type="application/json",
            )

        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["usage"]["band"], "peak")
        self.assertEqual(payload["usage"]["band_display"], "高峰")
        self.assertEqual(payload["usage"]["cost_display"], "0.0036")
        self.assertEqual(payload["usage"]["prompt_tokens"], 1000)
        # 内部 _usage 键不得泄漏进业务 data
        self.assertNotIn("_usage", payload["data"])

    def test_response_without_usage_has_no_usage_field(self):
        user = User.objects.create_user(username="viewer2", password="pass")
        self.client.force_login(user)

        fake_result = {
            "phonetic": [], "parts_and_means": [],
            "simple_meaning": [], "src_tts": "",
        }
        with patch("EAW.views.call_deepseek_api", return_value=fake_result):
            response = self.client.post(
                "/deepseek/query/",
                data=json.dumps({"word": "apple"}),
                content_type="application/json",
            )
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertNotIn("usage", payload)
