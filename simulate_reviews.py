#!/usr/bin/env python
"""
模拟脚本：创建10条Item并按指定概率（60%熟悉/40%不熟悉）运行复习流程。
每次复习日期为计划日期 + 随机0-2天逾期。
运行前请确保开发环境可用（已安装依赖、可访问db.sqlite3）。
"""
import os
import django
import random
import json
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EbbinghausAnywhere.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from EAW.models import Item, Category, Proficiency

INTERVALS = [0, 1, 2, 4, 7, 15, 30, 90, 180]
LAST_INTERVAL = INTERVALS[-1]

def create_user(username='simuser', password='simpass'):
    User = get_user_model()
    user, created = User.objects.get_or_create(username=username)
    if created:
        user.set_password(password)
        user.save()
    return user, password

def seed_items(user, count=10):
    cat, _ = Category.objects.get_or_create(user=user, name='模拟')
    items = []
    today = date.today()
    for i in range(count):
        init = today - timedelta(days=random.randint(0, 30))
        itm = Item.objects.create(
            user=user,
            category=cat,
            item=f'sim_word_{i+1}',
            content='自动生成的测试单词',
            inputDate=init,
            initDate=init,
            current_interval=0,
            next_review_date=init + timedelta(days=0),
            proficiency=Proficiency.UNFAMILIAR,
            unfamiliar_history=[],
            needs_extra_review=False,
            extra_review_since=None,
        )
        items.append(itm)
    return items

def simulate_review_flow(user, password, items, p_yes=0.6, max_steps=12):
    client = Client()
    logged = client.login(username=user.username, password=password)
    if not logged:
        raise RuntimeError('无法通过 test client 登录')

    stats = {'total': len(items), 'finished': 0, 'actions': 0}
    logs = []

    for itm in items:
        steps = 0
        while steps < max_steps:
            itm.refresh_from_db()
            # 如果已经到最后一个间隔则停止
            if itm.current_interval == LAST_INTERVAL:
                logs.append((itm.id, 'finished', itm.current_interval))
                stats['finished'] += 1
                break

            # 计算本次复习日期：计划日 + 0-2 天逾期
            base = itm.next_review_date or date.today()
            review_date = base + timedelta(days=random.randint(0, 2))

            # 决定 YES/NO
            is_yes = random.random() < p_yes
            url = '/review-feedback/yes/' if is_yes else '/review-feedback/no/'
            payload = {'id': itm.id, 'date': review_date.isoformat()}
            resp = client.post(url, data=json.dumps(payload), content_type='application/json')
            stats['actions'] += 1
            steps += 1

            # 记录结果
            try:
                data = resp.json()
            except Exception:
                data = {'success': False, 'message': 'no json'}

            logs.append((itm.id, 'YES' if is_yes else 'NO', review_date.isoformat(), data.get('success'), itm.current_interval))

            # Refresh and continue
            itm.refresh_from_db()

            # Safety: if next_review_date is None, break
            if not itm.next_review_date:
                break

        # end while

    return stats, logs

def summarize(logs):
    from collections import Counter
    c = Counter([r[1] for r in logs])
    print('Actions summary:', dict(c))
    # show last state per item
    last = {}
    for r in logs:
        last[r[0]] = r
    for k, v in last.items():
        print('Item', k, 'last action', v)

if __name__ == '__main__':
    user, pwd = create_user()
    items = seed_items(user, 10)
    print(f'已创建 {len(items)} 条 Item，开始模拟复习流程...')
    stats, logs = simulate_review_flow(user, pwd, items, p_yes=0.6, max_steps=12)
    print('模拟完成，统计：', stats)
    summarize(logs)
