#!/usr/bin/env python
"""
测试复习场景：点NO后的额外复习逻辑
"""
import os
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EbbinghausAnywhere.settings')
django.setup()

from EAW.models import Item, Proficiency
from django.contrib.auth.models import User

# 获取测试用户
user = User.objects.first()
if not user:
    print("没有找到用户")
    exit()

# 查找一个测试单词
item = Item.objects.filter(user=user).first()
if not item:
    print("没有找到单词")
    exit()

print(f"测试单词: {item.item}")
print(f"current_interval: {item.current_interval}")
print(f"next_review_date: {item.next_review_date}")
print(f"needs_extra_review: {item.needs_extra_review}")
print(f"extra_review_since: {item.extra_review_since}")
print(f"proficiency: {item.proficiency}")
print(f"unfamiliar_history: {item.unfamiliar_history}")

# 模拟查询逻辑
today = datetime.today().date()
print(f"\n今天是: {today}")

from django.db.models import Q

# 测试查询条件
query1 = Q(next_review_date__lte=today)
query2 = Q(needs_extra_review=True, extra_review_since__lte=today)

match1 = Item.objects.filter(user=user, id=item.id).filter(query1).exists()
match2 = Item.objects.filter(user=user, id=item.id).filter(query2).exists()

print(f"\n匹配 next_review_date <= today: {match1}")
print(f"匹配 needs_extra_review=True and extra_review_since <= today: {match2}")
print(f"应该显示在复习列表: {match1 or match2}")
