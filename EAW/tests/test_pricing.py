"""
Tests for DeepSeek peak/off-peak pricing pure logic (EAW/pricing.py).
Covers the full checklist in《DeepSeek_API_峰谷定价适配指南》§8:
time-band boundaries (half-open), timezone conversion, naive datetimes,
cache-split billing without double counting, and peak-unconfigured fallback.
"""
from datetime import datetime, timezone
from decimal import Decimal

from django.test import SimpleTestCase

from EAW.pricing import (
    BAND_OFFPEAK,
    BAND_PEAK,
    DEFAULT_MODEL,
    PriceTier,
    SHANGHAI,
    calculate_cost,
    is_peak_time,
    normalize_model_name,
    resolve_band,
    resolve_tier,
)


# 新价格表（指南§2，元/百万 tokens）
FLASH_OFFPEAK = PriceTier(Decimal("0.05"), Decimal("1.50"), Decimal("4.50"))
FLASH_PEAK = PriceTier(Decimal("0.10"), Decimal("3.00"), Decimal("9.00"))
PRO_OFFPEAK = PriceTier(Decimal("0.15"), Decimal("4.50"), Decimal("13.50"))
UNCONFIGURED_PEAK = PriceTier(Decimal("0"), Decimal("0"), Decimal("0"))

# 2026-08-18 是周二；2026-08-23 是周日（官方口径不区分周末）


def sh(y, m, d, h, mi=0, s=0):
    """构造北京时间的 aware datetime。"""
    return datetime(y, m, d, h, mi, s, tzinfo=SHANGHAI)


class TestIsPeakTimeBoundaries(SimpleTestCase):
    """半开区间 [9:00,12:00) ∪ [14:00,18:00)：9:00/14:00 含，12:00/18:00 排。"""

    def test_0900_inclusive_is_peak(self):
        self.assertTrue(is_peak_time(sh(2026, 8, 18, 9, 0, 0)))

    def test_1200_exclusive_is_offpeak_noon(self):
        self.assertFalse(is_peak_time(sh(2026, 8, 18, 12, 0, 0)))

    def test_1230_noon_is_offpeak(self):
        self.assertFalse(is_peak_time(sh(2026, 8, 18, 12, 30, 0)))

    def test_1400_inclusive_is_peak(self):
        self.assertTrue(is_peak_time(sh(2026, 8, 18, 14, 0, 0)))

    def test_1800_exclusive_is_offpeak(self):
        self.assertFalse(is_peak_time(sh(2026, 8, 18, 18, 0, 0)))

    def test_085959_before_peak(self):
        self.assertFalse(is_peak_time(sh(2026, 8, 18, 8, 59, 59)))

    def test_2300_night_is_offpeak(self):
        self.assertFalse(is_peak_time(sh(2026, 8, 18, 23, 0, 0)))

    def test_sunday_morning_is_peak(self):
        """官方未区分工作日/周末：周日 10:00 仍为高峰。"""
        self.assertTrue(is_peak_time(sh(2026, 8, 23, 10, 0, 0)))


class TestIsPeakTimeTimezone(SimpleTestCase):
    """高峰定义锚定北京时间，任意时区 aware datetime 必须先换算。"""

    def test_utc_0130_equals_beijing_0930_peak(self):
        moment = datetime(2026, 8, 18, 1, 30, 0, tzinfo=timezone.utc)
        self.assertTrue(is_peak_time(moment))

    def test_utc_0359_equals_beijing_1159_peak(self):
        moment = datetime(2026, 8, 18, 3, 59, 0, tzinfo=timezone.utc)
        self.assertTrue(is_peak_time(moment))

    def test_utc_0400_equals_beijing_1200_offpeak(self):
        moment = datetime(2026, 8, 18, 4, 0, 0, tzinfo=timezone.utc)
        self.assertFalse(is_peak_time(moment))

    def test_naive_datetime_interpreted_as_beijing(self):
        self.assertTrue(is_peak_time(datetime(2026, 8, 18, 9, 30, 0)))
        self.assertFalse(is_peak_time(datetime(2026, 8, 18, 12, 30, 0)))


class TestResolveBand(SimpleTestCase):
    def test_resolve_band_peak(self):
        self.assertEqual(resolve_band(sh(2026, 8, 18, 10, 0, 0)), BAND_PEAK)

    def test_resolve_band_offpeak(self):
        self.assertEqual(resolve_band(sh(2026, 8, 18, 19, 0, 0)), BAND_OFFPEAK)

    def test_resolve_band_default_now_returns_valid_band(self):
        self.assertIn(resolve_band(), (BAND_PEAK, BAND_OFFPEAK))


class TestNormalizeModelName(SimpleTestCase):
    """旧名 deepseek-chat/deepseek-reasoner 价格跟 v4-flash 走（指南§2）。"""

    def test_legacy_chat_maps_to_flash(self):
        self.assertEqual(normalize_model_name("deepseek-chat"), DEFAULT_MODEL)

    def test_legacy_reasoner_maps_to_flash(self):
        self.assertEqual(normalize_model_name("deepseek-reasoner"), DEFAULT_MODEL)

    def test_current_names_unchanged(self):
        self.assertEqual(normalize_model_name("deepseek-v4-flash"), "deepseek-v4-flash")
        self.assertEqual(normalize_model_name("deepseek-v4-pro"), "deepseek-v4-pro")


class TestPriceTier(SimpleTestCase):
    def test_all_positive_is_configured(self):
        self.assertTrue(FLASH_OFFPEAK.is_configured)

    def test_any_zero_is_not_configured(self):
        self.assertFalse(UNCONFIGURED_PEAK.is_configured)
        partial = PriceTier(Decimal("0.10"), Decimal("0"), Decimal("9.00"))
        self.assertFalse(partial.is_configured)


class TestCalculateCost(SimpleTestCase):
    """费用 = (prompt-cached)×未命中 + cached×命中 + output×输出，除以 1e6。"""

    def test_cache_split_billing_flash_offpeak(self):
        # (600×1.50 + 400×0.05 + 200×4.50) / 1e6 = 1820/1e6
        cost = calculate_cost(1000, 400, 200, FLASH_OFFPEAK)
        self.assertEqual(cost, Decimal("0.0018200000"))

    def test_cache_split_billing_pro_offpeak(self):
        # (600×4.50 + 400×0.15 + 200×13.50) / 1e6 = 5460/1e6
        cost = calculate_cost(1000, 400, 200, PRO_OFFPEAK)
        self.assertEqual(cost, Decimal("0.0054600000"))

    def test_fully_cached_input_has_no_miss_charge(self):
        # cached == prompt → 未命中部分为 0：(0×1.50 + 1000×0.05 + 200×4.50)/1e6
        cost = calculate_cost(1000, 1000, 200, FLASH_OFFPEAK)
        self.assertEqual(cost, Decimal("0.0009500000"))

    def test_cached_exceeding_prompt_clamps_to_zero(self):
        # 防御：cached > prompt 时未命中部分不得为负
        cost = calculate_cost(100, 200, 50, FLASH_OFFPEAK)
        # (0×1.50 + 200×0.05 + 50×4.50)/1e6 = 235/1e6
        self.assertEqual(cost, Decimal("0.0002350000"))

    def test_peak_is_double_offpeak(self):
        offpeak_cost = calculate_cost(1000, 400, 200, FLASH_OFFPEAK)
        peak_cost = calculate_cost(1000, 400, 200, FLASH_PEAK)
        self.assertEqual(peak_cost, offpeak_cost * 2)

    def test_zero_usage_costs_zero(self):
        cost = calculate_cost(0, 0, 0, FLASH_OFFPEAK)
        self.assertEqual(cost, Decimal("0.0000000000"))


class TestResolveTier(SimpleTestCase):
    """band 记真实时段；峰时价未配置（列≤0）时价格回退闲时档（指南§5）。"""

    def test_peak_time_with_configured_peak_uses_peak(self):
        band, tier = resolve_tier(FLASH_OFFPEAK, FLASH_PEAK, sh(2026, 8, 18, 10, 0, 0))
        self.assertEqual(band, BAND_PEAK)
        self.assertEqual(tier, FLASH_PEAK)

    def test_offpeak_time_uses_offpeak(self):
        band, tier = resolve_tier(FLASH_OFFPEAK, FLASH_PEAK, sh(2026, 8, 18, 20, 0, 0))
        self.assertEqual(band, BAND_OFFPEAK)
        self.assertEqual(tier, FLASH_OFFPEAK)

    def test_peak_time_with_unconfigured_peak_falls_back(self):
        band, tier = resolve_tier(FLASH_OFFPEAK, UNCONFIGURED_PEAK, sh(2026, 8, 18, 10, 0, 0))
        self.assertEqual(band, BAND_PEAK)
        self.assertEqual(tier, FLASH_OFFPEAK)

    def test_peak_time_with_partially_configured_peak_falls_back(self):
        partial = PriceTier(Decimal("0.10"), Decimal("0"), Decimal("9.00"))
        band, tier = resolve_tier(FLASH_OFFPEAK, partial, sh(2026, 8, 18, 10, 0, 0))
        self.assertEqual(band, BAND_PEAK)
        self.assertEqual(tier, FLASH_OFFPEAK)
