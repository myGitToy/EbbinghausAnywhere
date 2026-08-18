"""
Tests for the billing ORM layer (EAW/billing.py) and pricing models.
Covers: migration seed data, record_usage snapshots per band,
peak-unconfigured fallback audit, never-raises contract,
get_pricing_table / get_cost_summary aggregation.
"""
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase

from EAW.models import DeepSeekUsageLog, ModelPricing
from EAW.pricing import SHANGHAI
from EAW.billing import (
    extract_usage,
    get_cost_summary,
    get_pricing_table,
    record_usage,
)


def sh(y, m, d, h, mi=0, s=0):
    """构造北京时间的 aware datetime。"""
    return datetime(y, m, d, h, mi, s, tzinfo=SHANGHAI)


PEAK_NOW = sh(2026, 8, 18, 10, 0, 0)      # 周二 10:00 → 高峰
OFFPEAK_NOW = sh(2026, 8, 18, 20, 0, 0)   # 周二 20:00 → 空闲

# flash 闲价 (600×1.50 + 400×0.05 + 200×4.50)/1e6；峰价为其 2 倍
OFFPEAK_COST = Decimal("0.0018200000")
PEAK_COST = Decimal("0.0036400000")


class TestPricingSeed(TestCase):
    """迁移 0015 种子：flash/pro 两行，价格与指南§2 一致。"""

    def test_seed_has_exactly_two_models(self):
        names = set(ModelPricing.objects.values_list("model_name", flat=True))
        self.assertEqual(names, {"deepseek-v4-flash", "deepseek-v4-pro"})

    def test_flash_prices(self):
        row = ModelPricing.objects.get(model_name="deepseek-v4-flash")
        self.assertEqual(row.offpeak_cache_hit_price, Decimal("0.0500"))
        self.assertEqual(row.offpeak_cache_miss_price, Decimal("1.5000"))
        self.assertEqual(row.offpeak_output_price, Decimal("4.5000"))
        self.assertEqual(row.peak_cache_hit_price, Decimal("0.1000"))
        self.assertEqual(row.peak_cache_miss_price, Decimal("3.0000"))
        self.assertEqual(row.peak_output_price, Decimal("9.0000"))

    def test_pro_prices(self):
        row = ModelPricing.objects.get(model_name="deepseek-v4-pro")
        self.assertEqual(row.offpeak_cache_hit_price, Decimal("0.1500"))
        self.assertEqual(row.offpeak_cache_miss_price, Decimal("4.5000"))
        self.assertEqual(row.offpeak_output_price, Decimal("13.5000"))
        self.assertEqual(row.peak_cache_hit_price, Decimal("0.3000"))
        self.assertEqual(row.peak_cache_miss_price, Decimal("9.0000"))
        self.assertEqual(row.peak_output_price, Decimal("27.0000"))

    def test_price_source_marked(self):
        for row in ModelPricing.objects.all():
            self.assertIn("official-pricing", row.price_source)
        self.assertTrue(ModelPricing.objects.filter(pricing_updated_at__isnull=False).exists())


class TestExtractUsage(SimpleTestCase):
    """从 OpenAI SDK 响应提取 token 数，防御非真实 usage（MagicMock/None）。"""

    def _response(self, prompt, cached, output, details=True):
        usage = SimpleNamespace(
            prompt_tokens=prompt,
            completion_tokens=output,
            prompt_tokens_details=SimpleNamespace(cached_tokens=cached) if details else None,
        )
        return SimpleNamespace(usage=usage)

    def test_full_usage_extracted(self):
        self.assertEqual(extract_usage(self._response(1000, 400, 200)), (1000, 400, 200))

    def test_details_none_means_zero_cached(self):
        self.assertEqual(extract_usage(self._response(1000, 0, 200, details=False)), (1000, 0, 200))

    def test_usage_none_returns_none(self):
        self.assertIsNone(extract_usage(SimpleNamespace(usage=None)))

    def test_non_int_tokens_returns_none(self):
        """MagicMock 的 usage 属性不是 int —— 必须跳过，不得落库脏数据。"""
        self.assertIsNone(extract_usage(MagicMock()))

    def test_negative_tokens_returns_none(self):
        self.assertIsNone(extract_usage(self._response(-1, 0, 200)))

    def test_non_int_cached_treated_as_zero(self):
        resp = SimpleNamespace(
            usage=SimpleNamespace(
                prompt_tokens=1000,
                completion_tokens=200,
                prompt_tokens_details=SimpleNamespace(cached_tokens=MagicMock()),
            )
        )
        self.assertEqual(extract_usage(resp), (1000, 0, 200))


class TestRecordUsage(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="bill_tester", password="pass")

    def test_peak_time_snapshot_and_cost(self):
        log = record_usage(
            model="deepseek-v4-flash", user=self.user,
            prompt_tokens=1000, cached_tokens=400, output_tokens=200,
            now=PEAK_NOW,
        )
        self.assertIsNotNone(log)
        self.assertEqual(log.band, "peak")
        self.assertEqual(log.model, "deepseek-v4-flash")
        self.assertEqual(log.billed_cache_hit_price, Decimal("0.1000"))
        self.assertEqual(log.billed_cache_miss_price, Decimal("3.0000"))
        self.assertEqual(log.billed_output_price, Decimal("9.0000"))
        self.assertEqual(log.cost, PEAK_COST)
        self.assertEqual(log.billed_at, PEAK_NOW)
        self.assertEqual(DeepSeekUsageLog.objects.count(), 1)

    def test_offpeak_time_snapshot_and_cost(self):
        log = record_usage(
            model="deepseek-v4-flash", user=self.user,
            prompt_tokens=1000, cached_tokens=400, output_tokens=200,
            now=OFFPEAK_NOW,
        )
        self.assertEqual(log.band, "offpeak")
        self.assertEqual(log.billed_cache_miss_price, Decimal("1.5000"))
        self.assertEqual(log.cost, OFFPEAK_COST)

    def test_legacy_model_name_normalized(self):
        log = record_usage(
            model="deepseek-chat", user=self.user,
            prompt_tokens=1000, cached_tokens=400, output_tokens=200,
            now=OFFPEAK_NOW,
        )
        self.assertEqual(log.model, "deepseek-v4-flash")

    def test_user_none_allowed_for_background_calls(self):
        log = record_usage(
            model="deepseek-v4-flash", user=None,
            prompt_tokens=10, cached_tokens=0, output_tokens=5,
            now=OFFPEAK_NOW,
        )
        self.assertIsNone(log.user)

    def test_peak_unconfigured_falls_back_but_band_is_real(self):
        """峰列清零后：band 仍记真实时段 peak，单价快照回退闲价（审计可解释）。"""
        row = ModelPricing.objects.get(model_name="deepseek-v4-flash")
        row.peak_cache_hit_price = 0
        row.peak_cache_miss_price = 0
        row.peak_output_price = 0
        row.save()

        log = record_usage(
            model="deepseek-v4-flash", user=self.user,
            prompt_tokens=1000, cached_tokens=400, output_tokens=200,
            now=PEAK_NOW,
        )
        self.assertEqual(log.band, "peak")
        self.assertEqual(log.billed_cache_miss_price, Decimal("1.5000"))
        self.assertEqual(log.cost, OFFPEAK_COST)

    def test_unknown_model_returns_none_without_log(self):
        self.assertIsNone(
            record_usage(
                model="no-such-model", user=self.user,
                prompt_tokens=10, cached_tokens=0, output_tokens=5,
                now=OFFPEAK_NOW,
            )
        )
        self.assertEqual(DeepSeekUsageLog.objects.count(), 0)

    def test_never_raises_on_bad_input(self):
        """never-raises 契约：任何入参异常都吞掉返回 None，不抛给调用方。"""
        self.assertIsNone(record_usage(model=None, user=None, prompt_tokens=1, cached_tokens=0, output_tokens=1))
        self.assertIsNone(
            record_usage(
                model="deepseek-v4-flash", user=None,
                prompt_tokens="not-an-int", cached_tokens=0, output_tokens=1,
                now=OFFPEAK_NOW,
            )
        )
        self.assertEqual(DeepSeekUsageLog.objects.count(), 0)


class TestGetPricingTable(TestCase):
    def test_table_rows_and_display_format(self):
        table = get_pricing_table()
        self.assertEqual(len(table), 2)
        flash = next(row for row in table if row["model"] == "deepseek-v4-flash")
        self.assertEqual(flash["cache_hit"], "闲 0.05 / 峰 0.1")
        self.assertEqual(flash["cache_miss"], "闲 1.5 / 峰 3")
        self.assertEqual(flash["output"], "闲 4.5 / 峰 9")
        self.assertTrue(flash["peak_enabled"])

    def test_peak_disabled_shows_offpeak_only(self):
        row = ModelPricing.objects.get(model_name="deepseek-v4-flash")
        row.peak_cache_hit_price = 0
        row.peak_cache_miss_price = 0
        row.peak_output_price = 0
        row.save()

        flash = next(r for r in get_pricing_table() if r["model"] == "deepseek-v4-flash")
        self.assertEqual(flash["cache_miss"], "闲 1.5")
        self.assertFalse(flash["peak_enabled"])


class TestGetCostSummary(TestCase):
    def _log(self, cost, band, billed_at):
        return DeepSeekUsageLog.objects.create(
            user=None, model="deepseek-v4-flash", band=band,
            prompt_tokens=1000, cached_tokens=0, output_tokens=100,
            billed_cache_hit_price=Decimal("0.0500"),
            billed_cache_miss_price=Decimal("1.5000"),
            billed_output_price=Decimal("4.5000"),
            cost=cost, billed_at=billed_at,
        )

    def test_empty_summary_has_zero_cost(self):
        summary = get_cost_summary(now=OFFPEAK_NOW)
        self.assertEqual(summary["total_cost"], Decimal("0"))
        self.assertEqual(summary["month_cost"], Decimal("0"))
        self.assertEqual(summary["month_peak_cost"], Decimal("0"))
        self.assertIsNone(summary["peak_ratio"])

    def test_summary_aggregates_and_peak_ratio(self):
        # 8月内：peak 0.00364 + offpeak 0.00182；7月：peak 0.00364（不计入本月）
        self._log(PEAK_COST, "peak", PEAK_NOW)
        self._log(OFFPEAK_COST, "offpeak", OFFPEAK_NOW)
        self._log(PEAK_COST, "peak", sh(2026, 7, 15, 10, 0, 0))

        summary = get_cost_summary(now=OFFPEAK_NOW)
        # 累计含 7 月；本月只含 8 月两笔
        self.assertEqual(summary["total_cost"], PEAK_COST * 2 + OFFPEAK_COST)
        self.assertEqual(summary["month_cost"], PEAK_COST + OFFPEAK_COST)
        self.assertEqual(summary["month_peak_cost"], PEAK_COST)
        self.assertEqual(summary["peak_ratio"], "66.7%")  # 0.00364/0.00546

    def test_summary_without_peak_cost_shows_zero_ratio(self):
        """本月有费用但全部发生在空闲时段 → 占比显示 0.0%（比 None 更有信息量）。"""
        self._log(OFFPEAK_COST, "offpeak", OFFPEAK_NOW)
        summary = get_cost_summary(now=OFFPEAK_NOW)
        self.assertEqual(summary["peak_ratio"], "0.0%")
