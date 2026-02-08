"""
积分系统单元测试

测试积分系统的核心功能：
1. 用户积分账户管理
2. 积分历史记录
3. 用户配置管理
4. 兑换记录
5. 连续学习/签到逻辑
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from EAW.models import (
    UserPoints, PointHistory, UserPointsConfig,
    PointRedemption, UserStreak, Category, Item, Proficiency
)
import json


class UserPointsModelTest(TestCase):
    """测试UserPoints模型"""

    def setUp(self):
        """创建测试用户"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_create_points_account(self):
        """测试创建积分账户"""
        points = UserPoints.objects.create(user=self.user)
        self.assertEqual(points.current_points, 0)
        self.assertEqual(points.total_earned, 0)
        self.assertEqual(points.total_spent, 0)

    def test_add_points(self):
        """测试增加积分"""
        points = UserPoints.objects.create(user=self.user)

        # 增加10积分
        history = points.add_points(
            points=10,
            reason="测试奖励",
            reference_id="test_1"
        )

        # 验证积分增加
        points.refresh_from_db()
        self.assertEqual(points.current_points, 10)
        self.assertEqual(points.total_earned, 10)

        # 验证历史记录
        self.assertEqual(history.change_type, 'EARN')
        self.assertEqual(history.points, 10)
        self.assertEqual(history.balance_after, 10)

    def test_spend_points(self):
        """测试消费积分"""
        points = UserPoints.objects.create(user=self.user, current_points=100)

        # 消费30积分
        history = points.spend_points(
            points=30,
            reason="测试兑换",
            reference_id="test_2"
        )

        # 验证积分扣除
        points.refresh_from_db()
        self.assertEqual(points.current_points, 70)
        self.assertEqual(points.total_spent, 30)

        # 验证历史记录
        self.assertEqual(history.change_type, 'SPEND')
        self.assertEqual(history.points, -30)
        self.assertEqual(history.balance_after, 70)

    def test_spend_insufficient_points(self):
        """测试积分不足"""
        points = UserPoints.objects.create(user=self.user, current_points=10)

        # 尝试消费20积分（余额不足）
        with self.assertRaises(ValueError) as context:
            points.spend_points(
                points=20,
                reason="测试兑换"
            )

        self.assertIn("Insufficient points", str(context.exception))

    def test_negative_points(self):
        """测试负数积分"""
        points = UserPoints.objects.create(user=self.user)

        # 尝试增加负数积分
        with self.assertRaises(ValueError):
            points.add_points(points=-10, reason="测试")


class PointHistoryModelTest(TestCase):
    """测试PointHistory模型"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_history_creation(self):
        """测试历史记录创建"""
        history = PointHistory.objects.create(
            user=self.user,
            change_type='EARN',
            points=5,
            reason='测试',
            balance_after=5
        )

        self.assertEqual(history.user, self.user)
        self.assertEqual(history.change_type, 'EARN')
        self.assertEqual(history.points, 5)


class UserPointsConfigModelTest(TestCase):
    """测试UserPointsConfig模型"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_default_config(self):
        """测试默认配置"""
        config = UserPointsConfig.objects.create(user=self.user)

        self.assertEqual(config.minutes_per_point, 1.0)
        self.assertEqual(config.redemption_step, 10)
        self.assertEqual(config.min_redemption_minutes, 1)
        self.assertEqual(config.max_redemption_minutes, 300)
        self.assertTrue(config.daily_checkin_enabled)
        self.assertEqual(config.daily_checkin_points, 5)
        self.assertTrue(config.streak_reward_enabled)
        self.assertEqual(config.streak_reward_points, 5)
        self.assertEqual(config.streak_reward_days, 7)

    def test_custom_config(self):
        """测试自定义配置"""
        config = UserPointsConfig.objects.create(
            user=self.user,
            minutes_per_point=2.0,
            redemption_step=15,
            min_redemption_minutes=5,
            max_redemption_minutes=600
        )

        self.assertEqual(config.minutes_per_point, 2.0)
        self.assertEqual(config.redemption_step, 15)
        self.assertEqual(config.min_redemption_minutes, 5)
        self.assertEqual(config.max_redemption_minutes, 600)


class PointRedemptionModelTest(TestCase):
    """测试PointRedemption模型"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_redemption_creation(self):
        """测试创建兑换记录"""
        redemption = PointRedemption.objects.create(
            user=self.user,
            points_spent=10,
            game_minutes=10,
            exchange_rate=1.0,
            status='COMPLETED'
        )

        self.assertEqual(redemption.user, self.user)
        self.assertEqual(redemption.points_spent, 10)
        self.assertEqual(redemption.game_minutes, 10)
        self.assertEqual(redemption.status, 'COMPLETED')


class UserStreakModelTest(TestCase):
    """测试UserStreak模型"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.streak = UserStreak.objects.create(user=self.user)
        self.today = timezone.now().date()

    def test_initial_streak(self):
        """测试初始状态"""
        self.assertEqual(self.streak.current_streak, 0)
        self.assertEqual(self.streak.longest_streak, 0)
        self.assertEqual(self.streak.current_checkin_streak, 0)
        self.assertIsNone(self.streak.last_study_date)

    def test_update_study_streak_first_day(self):
        """测试第一次学习"""
        self.streak.update_study_streak(self.today)

        self.streak.refresh_from_db()
        self.assertEqual(self.streak.current_streak, 1)
        self.assertEqual(self.streak.last_study_date, self.today)

    def test_update_study_streak_consecutive_days(self):
        """测试连续学习"""
        yesterday = self.today - timedelta(days=1)

        # 设置昨天学习过
        self.streak.last_study_date = yesterday
        self.streak.current_streak = 5
        self.streak.save()

        # 今天学习
        self.streak.update_study_streak(self.today)

        self.streak.refresh_from_db()
        self.assertEqual(self.streak.current_streak, 6)
        self.assertEqual(self.streak.longest_streak, 6)

    def test_update_study_streak_break(self):
        """测试学习中断"""
        # 设置3天前学习过
        three_days_ago = self.today - timedelta(days=3)
        self.streak.last_study_date = three_days_ago
        self.streak.current_streak = 5
        self.streak.save()

        # 今天学习（中断后重新开始）
        self.streak.update_study_streak(self.today)

        self.streak.refresh_from_db()
        self.assertEqual(self.streak.current_streak, 1)
        self.assertEqual(self.streak.longest_streak, 5)

    def test_update_study_streak_same_day(self):
        """测试同一天多次学习"""
        self.streak.update_study_streak(self.today)
        first_count = self.streak.current_streak

        # 同一天再次学习
        self.streak.update_study_streak(self.today)

        self.streak.refresh_from_db()
        # 应该不变
        self.assertEqual(self.streak.current_streak, first_count)

    def test_update_checkin_streak(self):
        """测试签到连续性"""
        yesterday = self.today - timedelta(days=1)

        # 设置昨天签到
        self.streak.last_checkin_date = yesterday
        self.streak.current_checkin_streak = 3
        self.streak.save()

        # 今天签到
        self.streak.update_checkin_streak(self.today)

        self.streak.refresh_from_db()
        self.assertEqual(self.streak.current_checkin_streak, 4)

    def test_check_streak_reward(self):
        """测试连续学习奖励"""
        config = UserPointsConfig.objects.create(
            user=self.user,
            streak_reward_enabled=True,
            streak_reward_points=10,
            streak_reward_days=7
        )

        # 设置连续学习6天
        self.streak.current_streak = 6
        self.streak.last_study_date = self.today
        self.streak.save()

        # 第7天学习，应该触发奖励
        reward = self.streak.check_streak_reward(config)

        self.assertEqual(reward, 10)
        self.assertEqual(self.streak.current_streak, 7)
        self.assertEqual(self.streak.last_streak_reward_date, self.today)

    def test_check_streak_reward_already_given(self):
        """测试同一天不重复奖励"""
        config = UserPointsConfig.objects.create(
            user=self.user,
            streak_reward_enabled=True,
            streak_reward_points=10,
            streak_reward_days=7
        )

        # 设置已经奖励过
        self.streak.current_streak = 7
        self.streak.last_study_date = self.today
        self.streak.last_streak_reward_date = self.today
        self.streak.save()

        # 再次检查，不应该重复奖励
        reward = self.streak.check_streak_reward(config)

        self.assertEqual(reward, 0)

    def test_check_streak_reward_disabled(self):
        """测试奖励功能禁用"""
        config = UserPointsConfig.objects.create(
            user=self.user,
            streak_reward_enabled=False,
            streak_reward_points=10,
            streak_reward_days=7
        )

        self.streak.current_streak = 7
        self.streak.last_study_date = self.today
        self.streak.save()

        reward = self.streak.check_streak_reward(config)

        self.assertEqual(reward, 0)


class PointsIntegrationTest(TestCase):
    """积分系统集成测试"""

    def setUp(self):
        """创建测试数据"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.points = UserPoints.objects.create(user=self.user)
        self.config = UserPointsConfig.objects.create(user=self.user)
        self.streak = UserStreak.objects.create(user=self.user)
        self.today = timezone.now().date()

    def test_complete_points_flow(self):
        """测试完整的积分流程"""
        # 1. 复习获得积分
        self.points.add_points(
            points=1,
            reason="完成单词复习：test",
            reference_id="review_1"
        )
        self.assertEqual(self.points.current_points, 1)

        # 2. 签到获得积分
        self.streak.update_checkin_streak(self.today)
        self.points.add_points(
            points=self.config.daily_checkin_points,
            reason="每日签到（连续1天）",
            reference_id=f"checkin_{self.today}"
        )
        self.assertEqual(self.points.current_points, 6)

        # 3. 兑换游戏时长
        self.points.spend_points(
            points=2,
            reason=f"兑换{self.config.minutes_per_point * 2}分钟游戏时长",
            reference_id="redeem_test"
        )
        self.assertEqual(self.points.current_points, 4)

        # 4. 验证历史记录
        history_count = PointHistory.objects.filter(user=self.user).count()
        self.assertEqual(history_count, 3)  # EARN, EARN, SPEND

    def test_redemption_flow(self):
        """测试兑换流程"""
        # 给用户100积分
        self.points.add_points(points=100, reason="初始积分")

        # 兑换50分钟
        minutes_to_redeem = 50
        points_needed = int(minutes_to_redeem / self.config.minutes_per_point)

        redemption = PointRedemption.objects.create(
            user=self.user,
            points_spent=points_needed,
            game_minutes=minutes_to_redeem,
            exchange_rate=self.config.minutes_per_point
        )

        self.points.spend_points(
            points=points_needed,
            reason=f"兑换{minutes_to_redeem}分钟游戏时长",
            reference_id=f"redeem_{redemption.id}"
        )

        self.assertEqual(self.points.current_points, 100 - points_needed)
        self.assertEqual(redemption.status, 'COMPLETED')


class PointsAPITest(TestCase):
    """积分系统API测试"""

    def setUp(self):
        """创建测试数据"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        self.points = UserPoints.objects.create(user=self.user)
        self.config = UserPointsConfig.objects.create(user=self.user)

    def test_points_market_view(self):
        """测试积分商城页面"""
        response = self.client.get('/points/market/')
        self.assertEqual(response.status_code, 200)

    def test_points_config_view(self):
        """测试积分配置页面"""
        response = self.client.get('/points/config/')
        self.assertEqual(response.status_code, 200)

    def test_points_history_view(self):
        """测试积分历史页面"""
        response = self.client.get('/points/history/')
        self.assertEqual(response.status_code, 200)

    def test_redeem_api(self):
        """测试兑换API"""
        # 给用户100积分
        self.points.add_points(points=100, reason="初始积分")

        # 兑换30分钟
        response = self.client.post(
            '/points/redeem/',
            data=json.dumps({'minutes': 30}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        # 验证积分扣除
        self.points.refresh_from_db()
        self.assertEqual(self.points.current_points, 70)  # 100 - 30

    def test_redeem_insufficient_points(self):
        """测试积分不足"""
        # 用户只有10积分
        self.points.add_points(points=10, reason="初始积分")

        # 尝试兑换100分钟（需要100积分）
        response = self.client.post(
            '/points/redeem/',
            data=json.dumps({'minutes': 100}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['success'])

    def test_daily_checkin_api(self):
        """测试签到API"""
        response = self.client.post(
            '/points/checkin/',
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['points_earned'], self.config.daily_checkin_points)

        # 验证积分增加
        self.points.refresh_from_db()
        self.assertEqual(self.points.current_points, self.config.daily_checkin_points)

        # 同一天再次签到应该失败
        response = self.client.post(
            '/points/checkin/',
            content_type='application/json'
        )

        data = response.json()
        self.assertFalse(data['success'])

    def test_get_points_balance_api(self):
        """测试获取积分余额API"""
        self.points.add_points(points=50, reason="初始积分")

        response = self.client.get('/api/points/balance/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['current_points'], 50)


class EdgeCasesTest(TestCase):
    """边界情况测试"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        self.points = UserPoints.objects.create(user=self.user)
        self.config = UserPointsConfig.objects.create(user=self.user)

    def test_zero_redemption(self):
        """测试兑换0分钟"""
        response = self.client.post(
            '/points/redeem/',
            data=json.dumps({'minutes': 0}),
            content_type='application/json'
        )

        data = response.json()
        self.assertFalse(data['success'])

    def test_negative_redemption(self):
        """测试兑换负数分钟"""
        response = self.client.post(
            '/points/redeem/',
            data=json.dumps({'minutes': -10}),
            content_type='application/json'
        )

        data = response.json()
        self.assertFalse(data['success'])

    def test_exceed_max_redemption(self):
        """测试超过最大兑换时长"""
        self.points.add_points(points=1000, reason="初始积分")

        response = self.client.post(
            '/points/redeem/',
            data=json.dumps({'minutes': 1000}),  # 超过max_redemption_minutes(300)
            content_type='application/json'
        )

        data = response.json()
        self.assertFalse(data['success'])

    def test_custom_exchange_rate(self):
        """测试自定义汇率"""
        # 设置汇率为1积分=2分钟
        self.config.minutes_per_point = 2.0
        self.config.save()

        self.points.add_points(points=10, reason="初始积分")

        # 兑换20分钟（应该需要10积分）
        response = self.client.post(
            '/points/redeem/',
            data=json.dumps({'minutes': 20}),
            content_type='application/json'
        )

        data = response.json()
        self.assertTrue(data['success'])

        # 验证只扣除了10积分
        self.points.refresh_from_db()
        self.assertEqual(self.points.current_points, 0)


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner

    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["__main__"])
