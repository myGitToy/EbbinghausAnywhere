"""
测试签到功能

测试内容：
1. 普通签到获得5积分
2. 连续7天签到获得额外20积分奖励
"""

from django.contrib.auth.models import User
from EAW.models import UserPoints, UserStreak, UserPointsConfig, PointHistory
from datetime import date, timedelta
from django.test import Client
import json


def test_daily_checkin():
    """测试签到功能"""
    print("=" * 60)
    print("测试签到功能")
    print("=" * 60)

    # 创建测试用户
    username = "test_checkin_user"
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'password': 'test123'}
    )

    # 初始化用户数据
    points_account, _ = UserPoints.objects.get_or_create(
        user=user,
        defaults={
            'current_points': 0,
            'total_earned': 0,
            'total_spent': 0
        }
    )

    config, _ = UserPointsConfig.objects.get_or_create(
        user=user,
        defaults={
            'daily_checkin_enabled': True,
            'daily_checkin_points': 5
        }
    )

    streak, _ = UserStreak.objects.get_or_create(user=user)

    # 重置数据
    points_account.current_points = 0
    points_account.total_earned = 0
    points_account.total_spent = 0
    points_account.save()

    streak.current_checkin_streak = 0
    streak.last_checkin_date = None
    streak.save()

    # 清除签到历史
    PointHistory.objects.filter(
        user=user,
        reason__startswith='每日签到'
    ).delete()

    client = Client()
    client.force_login(user)

    print("\n测试场景1：连续签到6天（每天5积分）")
    print("-" * 60)

    for day in range(1, 7):
        # 模拟日期（需要手动更新last_checkin_date）
        test_date = date.today() - timedelta(days=6-day)

        # 重置streak状态，模拟连续签到
        streak.current_checkin_streak = day - 1
        streak.last_checkin_date = test_date - timedelta(days=1) if day > 1 else None
        streak.save()

        # 调用签到API
        response = client.post(
            '/points/checkin/',
            data=json.dumps({}),
            content_type='application/json'
        )

        response_data = json.loads(response.content)

        # 刷新数据
        points_account.refresh_from_db()
        streak.refresh_from_db()

        print(f"第{day}天签到：")
        print(f"  成功: {response_data['success']}")
        print(f"  消息: {response_data.get('message', 'N/A')}")
        print(f"  获得积分: {response_data.get('points_earned', 0)}")
        print(f"  当前积分: {points_account.current_points}")
        print(f"  连续签到: {streak.current_checkin_streak}天")

        # 验证
        expected_points = day * 5  # 每天积分
        assert response_data['success'], f"第{day}天签到失败"
        assert points_account.current_points == expected_points, \
            f"第{day}天后积分错误：期望{expected_points}，实际{points_account.current_points}"
        assert response_data.get('bonus_points', 0) == 0, \
            f"第{day}天不应该有额外奖励"

    print("\n✓ 连续6天签到测试通过！")

    print("\n测试场景2：第7天签到（连续7天额外奖励20积分）")
    print("-" * 60)

    # 设置为第6天
    streak.current_checkin_streak = 6
    streak.last_checkin_date = date.today() - timedelta(days=1)
    streak.save()

    # 第7天签到
    response = client.post(
        '/points/checkin/',
        data=json.dumps({}),
        content_type='application/json'
    )

    response_data = json.loads(response.content)
    points_account.refresh_from_db()
    streak.refresh_from_db()

    print(f"第7天签到：")
    print(f"  成功: {response_data['success']}")
    print(f"  消息: {response_data.get('message', 'N/A')}")
    print(f"  基础积分: {response_data.get('base_points', 0)}")
    print(f"  额外奖励: {response_data.get('bonus_points', 0)}")
    print(f"  总积分: {response_data.get('points_earned', 0)}")
    print(f"  当前总积分: {points_account.current_points}")
    print(f"  连续签到: {streak.current_checkin_streak}天")

    # 验证
    expected_total = 6 * 5 + 5 + 20  # 前6天30 + 第7天基础5 + 奖励20 = 55
    assert response_data['success'], "第7天签到失败"
    assert response_data.get('base_points', 0) == 5, "基础积分应该是5"
    assert response_data.get('bonus_points', 0) == 20, "额外奖励应该是20"
    assert response_data.get('points_earned', 0) == 25, "第7天总获得应该是25积分"
    assert points_account.current_points == expected_total, \
        f"第7天后总积分错误：期望{expected_total}，实际{points_account.current_points}"

    print("\n✓ 第7天额外奖励测试通过！")

    print("\n测试场景3：第14天签到（再次获得额外奖励）")
    print("-" * 60)

    # 设置为第13天
    streak.current_checkin_streak = 13
    streak.last_checkin_date = date.today() - timedelta(days=1)
    streak.save()

    # 第14天签到
    response = client.post(
        '/points/checkin/',
        data=json.dumps({}),
        content_type='application/json'
    )

    response_data = json.loads(response.content)
    points_account.refresh_from_db()
    streak.refresh_from_db()

    print(f"第14天签到：")
    print(f"  成功: {response_data['success']}")
    print(f"  消息: {response_data.get('message', 'N/A')}")
    print(f"  基础积分: {response_data.get('base_points', 0)}")
    print(f"  额外奖励: {response_data.get('bonus_points', 0)}")
    print(f"  总积分: {response_data.get('points_earned', 0)}")

    # 验证再次获得奖励
    assert response_data['success'], "第14天签到失败"
    assert response_data.get('bonus_points', 0) == 20, "第14天应该再次获得20积分奖励"

    print("\n✓ 第14天再次奖励测试通过！")

    print("\n测试场景4：检查积分历史记录")
    print("-" * 60)

    history = PointHistory.objects.filter(
        user=user,
        reason__startswith='每日签到'
    ).order_by('created_at')

    print(f"积分历史记录（共{history.count()}条）：")
    for record in history:
        print(f"  {record.created_at.strftime('%Y-%m-%d')} | "
              f"{record.reason} | {record.points:+d}积分 | "
              f"参考ID: {record.reference_id}")

    # 验证历史记录
    bonus_records = PointHistory.objects.filter(
        user=user,
        reason="连续签到7天奖励"
    )
    print(f"\n额外奖励记录数：{bonus_records.count()}")
    assert bonus_records.count() >= 2, "应该至少有2条额外奖励记录（第7天和第14天）"

    print("\n" + "=" * 60)
    print("✓ 所有测试通过！")
    print("=" * 60)

    # 清理测试数据
    print("\n清理测试数据...")
    user.delete()
    print("测试完成！")


if __name__ == '__main__':
    test_daily_checkin()
