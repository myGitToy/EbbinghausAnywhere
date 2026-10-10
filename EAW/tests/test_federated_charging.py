"""联邦积分代扣（#198）：SSO 绑定用户的 DeepSeek 消费切门户代扣。

覆盖 issue 定稿验证清单：
1. 联邦客户端（federated.py，mock requests）：预检/上报成功、unreachable、rejected、unconfigured、上报 payload 形状；
2. billing 分流接缝：precheck_ai_query（联邦 fail-closed / 本地原语义）、settle_federated_ai_query
   （成功标 ok 回写 ledger id / 明确拒绝标 failed / 网络失败保持 pending）；
3. record_usage 落 billing_party（SSO 绑定 → study_hub+pending；本地 → local+ok）；
4. 查询视图：联邦预检拒绝零 API 调用、成功上报、上报失败结果照常交付；本地用户路径零变化（无远程调用）。
"""
from datetime import datetime
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from EAW.billing import (
    FEDERATED_UNAVAILABLE_MESSAGE,
    _billing_party_for,
    hub_user_id_of,
    precheck_ai_query,
    settle_federated_ai_query,
)
from EAW.models import DeepSeekUsageLog, UserPoints, UserProfile

SHANGHAI = timezone.get_fixed_timezone(480)


def make_user(username: str, points: int = 0, hub_user_id: str | None = None) -> User:
    user = User.objects.create_user(username=username, password='x')
    UserPoints.objects.create(user=user, current_points=points)
    if hub_user_id is not None:
        UserProfile.objects.create(user=user, study_hub_user_id=hub_user_id)
    return user


def make_usage_log(user: User) -> DeepSeekUsageLog:
    """按 record_usage 对联邦用户的真实产物造行：study_hub + pending"""
    return DeepSeekUsageLog.objects.create(
        user=user,
        model='deepseek-v4-flash',
        band='offpeak',
        prompt_tokens=1000,
        cached_tokens=200,
        output_tokens=500,
        billed_cache_hit_price=Decimal('0.05'),
        billed_cache_miss_price=Decimal('1.5'),
        billed_output_price=Decimal('4.5'),
        cost=Decimal('0.0031500000'),
        billed_at=datetime(2026, 10, 10, 20, 0, tzinfo=SHANGHAI),
        billing_party=DeepSeekUsageLog.BILLING_PARTY_STUDY_HUB,
        deduct_status=DeepSeekUsageLog.DEDUCT_PENDING,
    )


class HubUserIdOfTest(TestCase):
    def test_bound_profile_returns_id(self):
        user = make_user('bound', hub_user_id='hub-u-1')
        self.assertEqual(hub_user_id_of(user), 'hub-u-1')

    def test_unbound_and_empty_profile_return_none(self):
        user = make_user('local-only')
        UserProfile.objects.create(user=user)  # 未绑定：study_hub_user_id 为空
        self.assertIsNone(hub_user_id_of(user))
        self.assertIsNone(hub_user_id_of(User.objects.create_user('noprofile')))

    def test_billing_party_split(self):
        self.assertEqual(_billing_party_for(make_user('p-local', hub_user_id=None)), 'local')
        self.assertEqual(_billing_party_for(make_user('p-hub', hub_user_id='hub-2')), 'study_hub')
        self.assertEqual(_billing_party_for(None), 'local')


class FederatedClientTest(TestCase):
    """federated.py 纯函数（mock requests.post）"""

    def setUp(self):
        self.log = make_usage_log(make_user('client-u', hub_user_id='hub-c-1'))

    @mock.patch('EAW.federated.study_hub_secret', return_value='test-secret')
    @mock.patch('EAW.federated.requests.post')
    def test_precheck_success(self, post, _secret):
        post.return_value = mock.Mock(status_code=200, **{'json.return_value': {'balanceCents': 1000, 'canSpend': True}})
        import EAW.federated as fed
        data, reason = fed.precheck_balance('hub-c-1')
        self.assertIsNone(reason)
        self.assertTrue(data['canSpend'])
        _, kwargs = post.call_args
        self.assertEqual(kwargs['json'], {'appSecret': 'test-secret', 'userId': 'hub-c-1'})

    @mock.patch('EAW.federated.study_hub_secret', return_value='test-secret')
    @mock.patch('EAW.federated.requests.post', side_effect=__import__('requests').RequestException('boom'))
    def test_precheck_unreachable(self, post, _secret):
        import EAW.federated as fed
        data, reason = fed.precheck_balance('hub-c-1')
        self.assertIsNone(data)
        self.assertEqual(reason, 'unreachable')

    @mock.patch('EAW.federated.study_hub_secret', return_value='test-secret')
    @mock.patch('EAW.federated.requests.post')
    def test_report_rejected_and_invalid(self, post, _secret):
        import EAW.federated as fed
        post.return_value = mock.Mock(status_code=403)
        data, reason = fed.report_deduction('hub-c-1', self.log)
        self.assertIsNone(data)
        self.assertEqual(reason, 'rejected')
        post.return_value = mock.Mock(status_code=422, text='unpriced')
        data, reason = fed.report_deduction('hub-c-1', self.log)
        self.assertEqual(reason, 'invalid')

    @mock.patch('EAW.federated.study_hub_secret', return_value='test-secret')
    @mock.patch('EAW.federated.requests.post')
    def test_report_payload_shape(self, post, _secret):
        """上报 payload：传用量不传钱，幂等键 = 流水 id，occurredAt 带 +08:00 时区"""
        import EAW.federated as fed
        post.return_value = mock.Mock(status_code=200, **{'json.return_value': {'replayed': False}})
        fed.report_deduction('hub-c-1', self.log)
        payload = post.call_args.kwargs['json']
        self.assertEqual(payload['jobType'], 'ewa_word_lookup')
        self.assertEqual(payload['model'], 'deepseek-v4-flash')
        self.assertEqual(payload['inputTokens'], 1000)
        self.assertEqual(payload['cacheHitTokens'], 200)
        self.assertEqual(payload['outputTokens'], 500)
        self.assertEqual(payload['band'], 'offpeak')
        self.assertEqual(payload['idempotencyKey'], str(self.log.id))
        self.assertTrue(payload['occurredAt'].endswith('+08:00'))

    @mock.patch('EAW.federated.study_hub_secret', return_value='')
    def test_unconfigured(self, secret):
        import EAW.federated as fed
        data, reason = fed.precheck_balance('hub-c-1')
        self.assertEqual(reason, 'unconfigured')


class RecordUsagePartyTest(TestCase):
    """record_usage 落承担方与上报状态（patch billing 命名空间——函数是模块顶层导入引用）"""

    PRICING = dict(
        offpeak_cache_hit_price=Decimal('0.05'), offpeak_cache_miss_price=Decimal('1.5'),
        offpeak_output_price=Decimal('4.5'), peak_cache_hit_price=Decimal('0.1'),
        peak_cache_miss_price=Decimal('3'), peak_output_price=Decimal('9'), peak_enabled=True,
    )
    TIER = ('offpeak', mock.Mock(cache_hit_price=Decimal('0.05'), cache_miss_price=Decimal('1.5'), output_price=Decimal('4.5')))

    def _record(self, user):
        from EAW.billing import record_usage
        with mock.patch('EAW.billing.get_pricing_for_model', return_value=mock.Mock(**self.PRICING)), \
             mock.patch('EAW.billing.resolve_tier', return_value=self.TIER):
            return record_usage(model='deepseek-v4-flash', user=user, prompt_tokens=10, cached_tokens=0, output_tokens=5)

    def test_record_usage_federated_row_pending(self):
        log = self._record(make_user('ru-hub', hub_user_id='hub-ru'))
        self.assertEqual(log.billing_party, 'study_hub')
        self.assertEqual(log.deduct_status, DeepSeekUsageLog.DEDUCT_PENDING)

    def test_record_usage_local_row_ok(self):
        log = self._record(make_user('ru-local'))
        self.assertEqual(log.billing_party, 'local')
        self.assertEqual(log.deduct_status, DeepSeekUsageLog.DEDUCT_OK)


class BillingSeamTest(TestCase):
    """precheck_ai_query / settle_federated_ai_query 接缝分流"""

    def test_local_user_precheck_unchanged(self):
        user = make_user('seam-local', points=1)
        ok, reason, view = precheck_ai_query(user)
        self.assertTrue(ok)
        self.assertIsNone(reason)
        self.assertEqual(view, {'portal': False, 'balance': 1})

        account = UserPoints.objects.get(user=user)
        account.current_points = 0
        account.save()
        ok, reason, view = precheck_ai_query(user)
        self.assertFalse(ok)
        self.assertIn('积分不足', reason)
        self.assertFalse(view['portal'])

    def test_federated_precheck_fail_closed_on_unreachable(self):
        user = make_user('seam-hub', hub_user_id='hub-s-1')
        with mock.patch('EAW.federated.precheck_balance', return_value=(None, 'unreachable')):
            ok, reason, view = precheck_ai_query(user)
        self.assertFalse(ok)
        self.assertEqual(reason, FEDERATED_UNAVAILABLE_MESSAGE)
        self.assertEqual(view, {'portal': True, 'balance': None})

    def test_federated_precheck_insufficient(self):
        user = make_user('seam-hub2', hub_user_id='hub-s-2')
        with mock.patch('EAW.federated.precheck_balance', return_value=({'balanceCents': 0, 'canSpend': False}, None)):
            ok, reason, view = precheck_ai_query(user)
        self.assertFalse(ok)
        self.assertIn('门户积分不足', reason)
        self.assertEqual(view['balance'], 0)

    def test_federated_precheck_pass(self):
        user = make_user('seam-hub3', hub_user_id='hub-s-3')
        with mock.patch('EAW.federated.precheck_balance', return_value=({'balanceCents': 1000, 'canSpend': True}, None)):
            ok, reason, view = precheck_ai_query(user)
        self.assertTrue(ok)
        self.assertIsNone(reason)
        self.assertEqual(view, {'portal': True, 'balance': 1000})

    def test_settle_success_marks_ok_and_ledger_id(self):
        user = make_user('settle-ok', hub_user_id='hub-t-1')
        log = make_usage_log(user)
        remote = {'pointsLedgerId': 77, 'usageLedgerId': 501, 'balanceAfter': 950.2, 'deducted': True, 'replayed': False}
        with mock.patch('EAW.federated.report_deduction', return_value=(remote, None)):
            reported, reason, view = settle_federated_ai_query(user, log.id)
        self.assertTrue(reported)
        self.assertIsNone(reason)
        self.assertEqual(view['balance'], 950.2)
        log.refresh_from_db()
        self.assertEqual(log.deduct_status, DeepSeekUsageLog.DEDUCT_OK)
        self.assertEqual(log.remote_ledger_id, 77)

    def test_settle_unreachable_keeps_pending(self):
        user = make_user('settle-pending', hub_user_id='hub-t-2')
        log = make_usage_log(user)
        with mock.patch('EAW.federated.report_deduction', return_value=(None, 'unreachable')):
            reported, reason, view = settle_federated_ai_query(user, log.id)
        self.assertFalse(reported)
        self.assertEqual(reason, FEDERATED_UNAVAILABLE_MESSAGE)
        self.assertIsNone(view)
        log.refresh_from_db()
        self.assertEqual(log.deduct_status, DeepSeekUsageLog.DEDUCT_PENDING)
        self.assertIsNone(log.remote_ledger_id)

    def test_settle_rejected_marks_failed(self):
        """门户明确拒绝（密钥错/模型未配价）：标 failed，重试无意义，人工兜底"""
        user = make_user('settle-failed', hub_user_id='hub-t-3')
        log = make_usage_log(user)
        with mock.patch('EAW.federated.report_deduction', return_value=(None, 'rejected')):
            reported, reason, _view = settle_federated_ai_query(user, log.id)
        self.assertFalse(reported)
        log.refresh_from_db()
        self.assertEqual(log.deduct_status, DeepSeekUsageLog.DEDUCT_FAILED)

    def test_settle_without_usage_log_skips(self):
        user = make_user('settle-nolog', hub_user_id='hub-t-4')
        reported, reason, view = settle_federated_ai_query(user, None)
        self.assertFalse(reported)
        self.assertIsNone(view)


class FederatedQueryViewTest(TestCase):
    """查询视图：联邦用户动线（mock 掉门户客户端，不出网）"""

    def setUp(self):
        self.user = make_user('view-hub', points=9, hub_user_id='hub-v-1')
        self.client.force_login(self.user)
        self.url = reverse('deepseek-query')

    def test_get_renders_portal_balance(self):
        with mock.patch('EAW.federated.precheck_balance', return_value=({'balanceCents': 888, 'canSpend': True}, None)):
            resp = self.client.get(self.url)
        self.assertContains(resp, '门户积分余额')
        self.assertContains(resp, '888')

    def test_precheck_unreachable_blocks_without_api_call(self):
        """fail-closed 核心：门户不可达 → 拒绝且零 API 调用"""
        with mock.patch('EAW.views.call_deepseek_api') as api, \
             mock.patch('EAW.views.precheck_ai_query', return_value=(False, FEDERATED_UNAVAILABLE_MESSAGE, {'portal': True, 'balance': None})):
            resp = self.client.post(self.url, data={'word': 'cat'}, content_type='application/json')
        data = resp.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], FEDERATED_UNAVAILABLE_MESSAGE)
        api.assert_not_called()

    def test_portal_insufficient_blocks_without_api_call(self):
        with mock.patch('EAW.views.call_deepseek_api') as api, \
             mock.patch('EAW.views.precheck_ai_query',
                        return_value=(False, '门户积分不足，请到 study-hub 门户领取每周配额或找家长充值', {'portal': True, 'balance': 0})):
            resp = self.client.post(self.url, data={'word': 'cat'}, content_type='application/json')
        data = resp.json()
        self.assertFalse(data['success'])
        self.assertTrue(data['insufficient_points'])
        self.assertTrue(data['portal'])
        api.assert_not_called()

    def test_success_reports_deduction_and_returns_portal_balance(self):
        result = {'phonetic': ['英', '美'], 'simple_meaning': ['简明释义: 测试'], 'parts_and_means': [],
                  '_usage': {'id': 7, 'band': 'offpeak', 'cost': '0.0012', 'prompt_tokens': 10, 'cached_tokens': 0, 'output_tokens': 5}}
        with mock.patch('EAW.views.precheck_ai_query', return_value=(True, None, {'portal': True, 'balance': 1000})), \
             mock.patch('EAW.views.call_deepseek_api', return_value=dict(result)), \
             mock.patch('EAW.views.settle_federated_ai_query',
                        return_value=(True, None, {'portal': True, 'balance': 950.2})):
            resp = self.client.post(self.url, data={'word': 'cat'}, content_type='application/json')
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['portal'])
        self.assertEqual(data['balance'], 950.2)
        self.assertNotIn('id', data.get('usage', {}))
        # 本地积分不被扣（联邦用户本地账本不参与 AI 计费，Q4）
        self.user.refresh_from_db()
        self.assertEqual(self.user.points_account.current_points, 9)

    def test_report_failure_still_delivers_result(self):
        """上报失败：查询结果照常交付（fail-closed 只在预检面），余额回落预检值"""
        result = {'phonetic': ['英'], 'simple_meaning': ['简明释义: x'], 'parts_and_means': [],
                  '_usage': {'id': 8, 'band': 'peak', 'cost': '0.002', 'prompt_tokens': 10, 'cached_tokens': 0, 'output_tokens': 5}}
        with mock.patch('EAW.views.precheck_ai_query', return_value=(True, None, {'portal': True, 'balance': 1000})), \
             mock.patch('EAW.views.call_deepseek_api', return_value=dict(result)), \
             mock.patch('EAW.views.settle_federated_ai_query', return_value=(False, FEDERATED_UNAVAILABLE_MESSAGE, None)):
            resp = self.client.post(self.url, data={'word': 'cat'}, content_type='application/json')
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['balance'], 1000)  # 预检带回的余额

    def test_local_user_has_zero_remote_calls(self):
        """本地用户路径零变化：全程无任何门户调用（#198 定稿：本地路径不受联邦化影响）"""
        local = make_user('view-local', points=2)
        self.client.force_login(local)
        result = {'phonetic': ['英'], 'simple_meaning': ['简明释义: x'], 'parts_and_means': [],
                  '_usage': {'id': 9, 'band': 'offpeak', 'cost': '0.001', 'prompt_tokens': 10, 'cached_tokens': 0, 'output_tokens': 5}}
        with mock.patch('EAW.views.call_deepseek_api', return_value=dict(result)), \
             mock.patch('EAW.federated.requests.post') as remote:
            resp = self.client.post(self.url, data={'word': 'cat'}, content_type='application/json')
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertNotIn('portal', data)
        self.assertEqual(data['balance'], 2 - 1)
        remote.assert_not_called()
        local.refresh_from_db()
        self.assertEqual(local.points_account.current_points, 1)
