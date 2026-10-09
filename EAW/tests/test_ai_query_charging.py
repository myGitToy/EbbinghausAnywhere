"""DeepSeek 查询积分门槛（#197）：零门槛资损缺口收口。

覆盖 issue 定稿测试清单：
1. 余额充足：查询成功扣 1 分，PointHistory 流水与余额正确；
2. 余额 0：拒绝请求，不产生 DeepSeek 调用（mock 断言零调用）；
3. DeepSeek 调用失败/返回空：不扣分；
4. SSO 影子号用户行为一致（本期统一本地计费）；
5. charge_ai_query 接缝单测（无账户拒绝；#198 联邦化分流点存在）。
"""
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from EAW.billing import AI_QUERY_COST_POINTS, ai_query_balance, charge_ai_query
from EAW.models import PointHistory, UserPoints, UserProfile

MOCK_SUCCESS_RESULT = {
    'phonetic': ['英', '美'],
    'simple_meaning': ['简明释义: 测试'],
    'parts_and_means': [],
    '_usage': {'id': 7, 'band': 'offpeak', 'cost': '0.0012', 'prompt_tokens': 10, 'cached_tokens': 0, 'output_tokens': 5},
}


def make_user(username: str, points: int) -> tuple[User, UserPoints]:
    user = User.objects.create_user(username=username, password='x')
    account = UserPoints.objects.create(user=user, current_points=points)
    return user, account


class ChargeAiQueryTest(TestCase):
    """charge_ai_query 接缝单测（#198 联邦化的扣费分流点所在）"""

    def setUp(self):
        self.user, self.account = make_user('quser', 5)

    def test_charge_success_deducts_one_and_writes_history(self):
        ok, reason = charge_ai_query(self.user, reference_id='42')
        self.assertTrue(ok)
        self.assertIsNone(reason)
        self.account.refresh_from_db()
        self.assertEqual(self.account.current_points, 5 - AI_QUERY_COST_POINTS)
        history = PointHistory.objects.filter(user=self.user, reason='DeepSeek 单词查询').latest('id')
        self.assertEqual(history.points, -AI_QUERY_COST_POINTS)
        self.assertEqual(history.change_type, 'SPEND')
        self.assertEqual(history.reference_id, '42')

    def test_charge_insufficient_rejected(self):
        self.account.current_points = 0
        self.account.save()
        ok, reason = charge_ai_query(self.user)
        self.assertFalse(ok)
        self.assertIn('积分不足', reason)
        self.account.refresh_from_db()
        self.assertEqual(self.account.current_points, 0)

    def test_charge_without_account_rejected(self):
        user2 = User.objects.create_user(username='noaccount', password='x')
        ok, reason = charge_ai_query(user2)
        self.assertFalse(ok)
        self.assertIn('积分不足', reason)

    def test_sso_shadow_user_same_local_billing(self):
        """SSO 影子号本期统一本地积分计费（#198 落地后才切门户代扣）"""
        UserProfile.objects.create(user=self.user, study_hub_user_id='hub-user-1')
        ok, _ = charge_ai_query(self.user)
        self.assertTrue(ok)
        self.account.refresh_from_db()
        self.assertEqual(self.account.current_points, 5 - AI_QUERY_COST_POINTS)


class DeepSeekQueryViewGateTest(TestCase):
    """查询视图门槛：预检拒绝零 API 调用；成功扣 1；失败不扣"""

    def setUp(self):
        self.user, self.account = make_user('viewuser', 3)
        self.client.force_login(self.user)
        self.url = reverse('deepseek-query')

    def test_zero_balance_rejects_without_api_call(self):
        self.account.current_points = 0
        self.account.save()
        with mock.patch('EAW.views.call_deepseek_api') as api:
            resp = self.client.post(self.url, data={'word': 'cat'}, content_type='application/json')
        data = resp.json()
        self.assertFalse(data['success'])
        self.assertTrue(data['insufficient_points'])
        self.assertEqual(data['balance'], 0)
        api.assert_not_called()  # 零门槛缺口收口的核心断言：余额 0 不产生任何真实调用

    def test_success_charges_one_and_returns_balance(self):
        with mock.patch('EAW.views.call_deepseek_api', return_value=dict(MOCK_SUCCESS_RESULT)):
            resp = self.client.post(self.url, data={'word': 'cat'}, content_type='application/json')
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['balance'], 3 - AI_QUERY_COST_POINTS)
        self.account.refresh_from_db()
        self.assertEqual(self.account.current_points, 3 - AI_QUERY_COST_POINTS)
        # PointHistory 关联本次 DeepSeekUsageLog id
        history = PointHistory.objects.filter(user=self.user, reason='DeepSeek 单词查询').latest('id')
        self.assertEqual(history.reference_id, '7')
        # 响应侧剥离内部流水 id
        self.assertNotIn('id', data.get('usage', {}))

    def test_api_failure_no_charge(self):
        with mock.patch('EAW.views.call_deepseek_api', return_value=None):
            resp = self.client.post(self.url, data={'word': 'cat'}, content_type='application/json')
        data = resp.json()
        self.assertFalse(data['success'])
        self.account.refresh_from_db()
        self.assertEqual(self.account.current_points, 3)
        self.assertFalse(PointHistory.objects.filter(user=self.user, reason='DeepSeek 单词查询').exists())

    def test_insufficient_during_charge_rejected(self):
        """预检通过但扣费拒绝（并发窗口/mock 接缝）：拒绝返回查询结果，不漏扣"""
        with mock.patch('EAW.views.call_deepseek_api', return_value=dict(MOCK_SUCCESS_RESULT)), \
             mock.patch('EAW.views.charge_ai_query', return_value=(False, '积分不足，完成复习打卡可赚积分')):
            resp = self.client.post(self.url, data={'word': 'cat'}, content_type='application/json')
        data = resp.json()
        self.assertFalse(data['success'])
        self.assertTrue(data['insufficient_points'])
        self.account.refresh_from_db()
        self.assertEqual(self.account.current_points, 3)
