"""
测试签到连续奖励功能

测试内容：
1. 普通签到获得5积分
2. 连续7天签到获得额外20积分奖励
3. 第14天再次获得额外奖励
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from EAW.models import UserPoints, UserStreak, UserPointsConfig, PointHistory
from datetime import date, timedelta
import json


class DailyCheckinStreakBonusTest(TestCase):
    """测试每日签到连续奖励功能"""

    def setUp(self):
        """设置测试环境"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testcheckin',
            password='testpass123'
        )
        self.points_account = UserPoints.objects.create(
            user=self.user,
            current_points=0,
            total_earned=0,
            total_spent=0
        )
        self.config = UserPointsConfig.objects.create(
            user=self.user,
            daily_checkin_enabled=True,
            daily_checkin_points=5
        )
        self.streak = UserStreak.objects.create(
            user=self.user
        )

    def test_first_checkin_earns_5_points(self):
        """测试首次签到获得5积分"""
        self.client.login(username='testcheckin', password='testpass123')

        response = self.client.post(
            '/points/checkin/',
            data=json.dumps({}),
            content_type='application/json'
        )

        response_data = json.loads(response.content)

        # 验证响应
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['points_earned'], 5)
        self.assertEqual(response_data.get('base_points'), 5)
        self.assertEqual(response_data.get('bonus_points', 0), 0)

        # 验证数据库
        self.points_account.refresh_from_db()
        self.streak.refresh_from_db()

        self.assertEqual(self.points_account.current_points, 5)
        self.assertEqual(self.streak.current_checkin_streak, 1)

    def test_consecutive_7_days_gets_20_bonus(self):
        """测试连续7天签到获得额外20积分奖励"""
        self.client.login(username='testcheckin', password='testpass123')

        # 直接设置第6天签到完成的状态
        self.streak.current_checkin_streak = 6
        self.streak.last_checkin_date = date.today() - timedelta(days=1)
        self.streak.save()

        # 设置前6天的积分（6天 × 5积分 = 30）
        self.points_account.current_points = 30
        self.points_account.total_earned = 30
        self.points_account.save()

        # 第7天签到
        response = self.client.post(
            '/points/checkin/',
            data=json.dumps({}),
            content_type='application/json'
        )

        response_data = json.loads(response.content)

        # 验证第7天有额外奖励
        self.assertTrue(response_data['success'], f"签到失败: {response_data.get('message')}")
        self.assertEqual(response_data['base_points'], 5, "基础积分应该是5")
        self.assertEqual(response_data['bonus_points'], 20, "额外奖励应该是20")
        self.assertEqual(response_data['points_earned'], 25, "总获得应该是25")

        # 验证总积分：前6天30 + 第7天25 = 55
        self.points_account.refresh_from_db()
        expected_total = 55
        self.assertEqual(self.points_account.current_points, expected_total,
                        f"第7天后总积分应该是{expected_total}")

        # 验证连续签到天数
        self.streak.refresh_from_db()
        self.assertEqual(self.streak.current_checkin_streak, 7)

    def test_14_days_gets_bonus_twice(self):
        """测试第14天再次获得额外奖励"""
        self.client.login(username='testcheckin', password='testpass123')

        # 设置为第13天
        self.streak.current_checkin_streak = 13
        self.streak.last_checkin_date = date.today() - timedelta(days=1)
        self.streak.save()

        response = self.client.post(
            '/points/checkin/',
            data=json.dumps({}),
            content_type='application/json'
        )

        response_data = json.loads(response.content)

        # 验证第14天也有额外奖励
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['bonus_points'], 20,
                        "第14天应该再次获得20积分奖励")

    def test_checkin_creates_bonus_history_record(self):
        """测试签到额外奖励创建历史记录"""
        self.client.login(username='testcheckin', password='testpass123')

        # 设置为第6天
        self.streak.current_checkin_streak = 6
        self.streak.last_checkin_date = date.today() - timedelta(days=1)
        self.streak.save()

        # 第7天签到
        response = self.client.post(
            '/points/checkin/',
            data=json.dumps({}),
            content_type='application/json'
        )

        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])

        # 验证有额外奖励记录
        bonus_history = PointHistory.objects.filter(
            user=self.user,
            reason="连续签到7天奖励"
        )

        self.assertEqual(bonus_history.count(), 1, "应该有1条额外奖励记录")
        self.assertEqual(bonus_history.first().points, 20, "额外奖励应该是20积分")
        self.assertIsNotNone(bonus_history.first().reference_id, "应该有参考ID")

    def test_checkin_response_message_includes_bonus(self):
        """测试签到响应消息包含额外奖励信息"""
        self.client.login(username='testcheckin', password='testpass123')

        # 第7天签到
        self.streak.current_checkin_streak = 6
        self.streak.last_checkin_date = date.today() - timedelta(days=1)
        self.streak.save()

        response = self.client.post(
            '/points/checkin/',
            data=json.dumps({}),
            content_type='application/json'
        )

        response_data = json.loads(response.content)

        # 验证消息包含额外奖励信息
        self.assertIn('连续', response_data['message'], "消息应该包含'连续'")
        self.assertIn('7', response_data['message'], "消息应该包含'7'")
        self.assertIn('20', response_data['message'], "消息应该包含'20'")
        self.assertIn('额外奖励', response_data['message'], "消息应该包含'额外奖励'")

    def test_non_bonus_day_no_extra_points(self):
        """测试非奖励天（如第5天）没有额外积分"""
        self.client.login(username='testcheckin', password='testpass123')

        # 设置为第4天
        self.streak.current_checkin_streak = 4
        self.streak.last_checkin_date = date.today() - timedelta(days=1)
        self.streak.save()

        response = self.client.post(
            '/points/checkin/',
            data=json.dumps({}),
            content_type='application/json'
        )

        response_data = json.loads(response.content)

        # 验证没有额外奖励
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['points_earned'], 5, "第5天应该只获得5积分")
        self.assertEqual(response_data.get('bonus_points', 0), 0, "第5天不应该有额外奖励")
