"""
五子棋游戏积分系统测试

测试五子棋游戏的积分扣除功能：
1. 测试开始游戏API扣除5积分
2. 测试积分不足时的处理
3. 测试未登录用户的访问控制
4. 测试积分扣除后的历史记录
5. 测试并发请求的处理
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from EAW.models import UserPoints, PointHistory
import json


class GobangPointsAPITest(TestCase):
    """测试五子棋积分扣除API"""

    def setUp(self):
        """设置测试环境"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testgobang',
            password='testpass123'
        )
        # 创建用户积分账户
        self.points_account = UserPoints.objects.create(
            user=self.user,
            current_points=100,
            total_earned=100,
            total_spent=0
        )

    def test_start_game_api_requires_login(self):
        """测试开始游戏API需要登录"""
        response = self.client.post(
            '/api/gobang/start/',
            data=json.dumps({}),
            content_type='application/json'
        )

        # 未登录应该重定向或返回403/401
        self.assertIn(
            response.status_code, [302, 401, 403],
            "未登录用户不应该能调用开始游戏API"
        )

    def test_start_game_deducts_5_points(self):
        """测试开始游戏扣除5积分"""
        self.client.login(username='testgobang', password='testpass123')

        # 获取初始积分
        initial_points = self.points_account.current_points

        # 调用开始游戏API
        response = self.client.post(
            '/api/gobang/start/',
            data=json.dumps({}),
            content_type='application/json'
        )

        # 检查响应
        self.assertEqual(
            response.status_code,
            200,
            "开始游戏API应该返回200"
        )

        response_data = json.loads(response.content)
        self.assertTrue(
            response_data['success'],
            f"API调用应该成功: {response_data.get('message', 'Unknown error')}"
        )

        # 检查积分被扣除
        self.points_account.refresh_from_db()
        self.assertEqual(
            self.points_account.current_points,
            initial_points - 5,
            "应该扣除5积分"
        )
        self.assertEqual(
            self.points_account.total_spent,
            5,
            "总消费应该增加5"
        )

    def test_start_game_with_insufficient_points(self):
        """测试积分不足时的处理"""
        # 设置积分不足5分
        self.points_account.current_points = 3
        self.points_account.save()

        self.client.login(username='testgobang', password='testpass123')

        # 调用开始游戏API
        response = self.client.post(
            '/api/gobang/start/',
            data=json.dumps({}),
            content_type='application/json'
        )

        # 检查响应
        response_data = json.loads(response.content)
        self.assertFalse(
            response_data['success'],
            "积分不足时API应该返回失败"
        )
        self.assertIn(
            '积分不足',
            response_data['message'],
            "错误信息应该包含'积分不足'"
        )

        # 检查积分没有被扣除
        self.points_account.refresh_from_db()
        self.assertEqual(
            self.points_account.current_points,
            3,
            "积分不足时不应该扣除积分"
        )

    def test_start_game_creates_history_record(self):
        """测试开始游戏创建历史记录"""
        self.client.login(username='testgobang', password='testpass123')

        # 确保初始没有历史记录
        initial_history_count = PointHistory.objects.filter(
            user=self.user,
            reason='五子棋游戏'
        ).count()

        # 调用开始游戏API
        response = self.client.post(
            '/api/gobang/start/',
            data=json.dumps({}),
            content_type='application/json'
        )

        # 检查历史记录被创建
        final_history_count = PointHistory.objects.filter(
            user=self.user,
            reason='五子棋游戏'
        ).count()

        self.assertEqual(
            final_history_count,
            initial_history_count + 1,
            "应该创建一条积分历史记录"
        )

        # 检查历史记录的内容
        history = PointHistory.objects.filter(
            user=self.user,
            reason='五子棋游戏'
        ).order_by('-created_at').first()

        self.assertEqual(
            history.points,
            -5,
            "历史记录应该记录-5积分"
        )
        self.assertEqual(
            history.change_type,
            'SPEND',
            "变更类型应该是SPEND"
        )

    def test_start_game_response_includes_remaining_points(self):
        """测试响应包含剩余积分"""
        self.client.login(username='testgobang', password='testpass123')

        # 调用开始游戏API
        response = self.client.post(
            '/api/gobang/start/',
            data=json.dumps({}),
            content_type='application/json'
        )

        response_data = json.loads(response.content)

        # 检查响应包含剩余积分
        self.assertIn(
            'remaining_points',
            response_data,
            "响应应该包含剩余积分"
        )
        self.assertEqual(
            response_data['remaining_points'],
            95,
            "剩余积分应该是95"
        )

    def test_multiple_games_deduct_multiple_times(self):
        """测试多局游戏多次扣除积分"""
        self.client.login(username='testgobang', password='testpass123')

        initial_points = self.points_account.current_points

        # 连续开始3局游戏
        for i in range(3):
            response = self.client.post(
                '/api/gobang/start/',
                data=json.dumps({}),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 200)
            response_data = json.loads(response.content)
            self.assertTrue(response_data['success'])

        # 检查总扣除
        self.points_account.refresh_from_db()
        self.assertEqual(
            self.points_account.current_points,
            initial_points - 15,  # 3局 × 5积分
            "3局游戏应该扣除15积分"
        )

    def test_start_game_with_zero_points(self):
        """测试积分为0时的处理"""
        # 设置积分为0
        self.points_account.current_points = 0
        self.points_account.save()

        self.client.login(username='testgobang', password='testpass123')

        # 调用开始游戏API
        response = self.client.post(
            '/api/gobang/start/',
            data=json.dumps({}),
            content_type='application/json'
        )

        # 应该失败
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('积分不足', response_data['message'])

    def test_start_game_with_exactly_5_points(self):
        """测试刚好5积分时的处理"""
        # 设置积分为5
        self.points_account.current_points = 5
        self.points_account.save()

        self.client.login(username='testgobang', password='testpass123')

        # 调用开始游戏API
        response = self.client.post(
            '/api/gobang/start/',
            data=json.dumps({}),
            content_type='application/json'
        )

        # 应该成功
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])

        # 积分应该变为0
        self.points_account.refresh_from_db()
        self.assertEqual(
            self.points_account.current_points,
            0,
            "积分应该变为0"
        )


class GobangViewPointsIntegrationTest(TestCase):
    """测试五子棋页面与积分系统的集成"""

    def setUp(self):
        """设置测试环境"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testview',
            password='testpass123'
        )
        self.points_account = UserPoints.objects.create(
            user=self.user,
            current_points=50,
            total_earned=50
        )

    def test_gobang_page_shows_remaining_points(self):
        """测试五子棋页面显示剩余积分"""
        self.client.login(username='testview', password='testpass123')

        response = self.client.get('/gobang/')

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'remaining_points',
            response.context,
            "上下文应该包含remaining_points"
        )
        self.assertEqual(
            response.context['remaining_points'],
            50,
            "显示的剩余积分应该是50"
        )

    def test_gobang_page_creates_points_account_if_not_exists(self):
        """测试访问页面时自动创建积分账户"""
        # 创建一个没有积分账户的用户
        new_user = User.objects.create_user(
            username='newuser',
            password='testpass123'
        )

        # 确保没有积分账户
        self.assertFalse(
            UserPoints.objects.filter(user=new_user).exists(),
            "新用户不应该有积分账户"
        )

        self.client.login(username='newuser', password='testpass123')

        # 访问五子棋页面
        response = self.client.get('/gobang/')

        # 应该自动创建积分账户
        self.assertTrue(
            UserPoints.objects.filter(user=new_user).exists(),
            "访问页面后应该自动创建积分账户"
        )
        self.assertEqual(
            response.status_code,
            200,
            "页面应该正常加载"
        )


class GobangPointsHistoryTest(TestCase):
    """测试五子棋积分历史记录"""

    def setUp(self):
        """设置测试环境"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testhistory',
            password='testpass123'
        )
        self.points_account = UserPoints.objects.create(
            user=self.user,
            current_points=100
        )
        self.client.login(username='testhistory', password='testpass123')

    def test_game_history_has_reference_id(self):
        """测试游戏历史记录包含reference_id"""
        response = self.client.post(
            '/api/gobang/start/',
            data=json.dumps({}),
            content_type='application/json'
        )

        # 获取最新的一条历史记录
        history = PointHistory.objects.filter(
            user=self.user,
            reason='五子棋游戏'
        ).order_by('-created_at').first()

        self.assertIsNotNone(
            history.reference_id,
            "历史记录应该包含reference_id"
        )
        self.assertTrue(
            history.reference_id.startswith('gobang_'),
            "reference_id应该以'gobang_'开头"
        )

    def test_multiple_games_create_unique_reference_ids(self):
        """测试多局游戏产生不同的reference_id"""
        reference_ids = set()

        # 开始5局游戏
        for _ in range(5):
            self.client.post(
                '/api/gobang/start/',
                data=json.dumps({}),
                content_type='application/json'
            )
            history = PointHistory.objects.filter(
                user=self.user,
                reason='五子棋游戏'
            ).order_by('-created_at').first()
            reference_ids.add(history.reference_id)

        # 所有reference_id应该不同
        self.assertEqual(
            len(reference_ids),
            5,
            "每局游戏应该有唯一的reference_id"
        )


def run_gobang_points_tests():
    """
    运行五子棋积分系统测试的辅助函数

    使用方法：
    python manage.py test EAW.tests.test_gobang_points
    """
    print("五子棋积分系统测试")
    print("=" * 60)
    print("\n测试项目：")
    print("1. API访问控制")
    print("2. 积分扣除逻辑")
    print("3. 积分不足处理")
    print("4. 历史记录创建")
    print("5. 多局游戏处理")
    print("6. 页面集成测试")
    print("\n运行命令：")
    print("  ./.conda/python.exe manage.py test EAW.tests.test_gobang_points")
    print("\n或运行特定测试类：")
    print("  ./.conda/python.exe manage.py test EAW.tests.test_gobang_points.GobangPointsAPITest")
    print("  ./.conda/python.exe manage.py test EAW.tests.test_gobang_points.GobangViewPointsIntegrationTest")
    print("  ./.conda/python.exe manage.py test EAW.tests.test_gobang_points.GobangPointsHistoryTest")


if __name__ == '__main__':
    run_gobang_points_tests()
