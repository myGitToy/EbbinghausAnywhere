#!/usr/bin/env python
"""
测试日历API
"""
import os
import sys
import django
from datetime import datetime, timedelta

# 设置Django环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EbbinghausAnywhere.settings')
django.setup()

from django.contrib.auth.models import User
from EAW.models import Item
from django.db.models import Q

def test_calendar_data():
    """测试日历数据查询"""
    print("=== 测试日历API数据查询 ===\n")
    
    # 获取第一个用户
    try:
        user = User.objects.first()
        if not user:
            print("❌ 没有找到用户")
            return
        
        print(f"✓ 测试用户: {user.username}\n")
        
        # 测试日期范围
        today = datetime.today().date()
        start_date = today - timedelta(days=7)
        end_date = today + timedelta(days=7)
        
        print(f"📅 测试日期范围: {start_date} 到 {end_date}\n")
        
        # 统计每天的数据
        for i in range((end_date - start_date).days + 1):
            d = start_date + timedelta(days=i)
            
            # 今日计划
            today_planned = Item.objects.filter(
                user=user,
                next_review_date=d
            ).count()
            
            # 额外复习
            extra_review = Item.objects.filter(
                user=user
            ).filter(
                Q(needs_extra_review=True, extra_review_since__lte=d, next_review_date__gt=d) |
                Q(next_review_date__isnull=True, needs_extra_review=True, extra_review_since__lte=d)
            ).count()
            
            if today_planned > 0 or extra_review > 0:
                print(f"{d}: 今日计划={today_planned}, 额外复习={extra_review}")
        
        print("\n✅ 测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_calendar_data()
