#!/usr/bin/env python
import os
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EbbinghausAnywhere.settings')
django.setup()

from EAW.models import Item

INTERVALS = [0, 1, 2, 4, 7, 15, 30, 90, 180]
MAX_IDX = len(INTERVALS) - 1

def inspect():
    total = Item.objects.count()
    gt = Item.objects.filter(current_interval__gt=MAX_IDX).count()
    print(f"Total items: {total}")
    print(f"Items with current_interval > {MAX_IDX}: {gt}")

    # 显示若干示例
    examples = Item.objects.filter(current_interval__gt=MAX_IDX)[:10]
    for it in examples:
        print(f"id={it.id} current_interval={it.current_interval} initDate={it.initDate} next_review_date={it.next_review_date}")

    # 检查 next_review_date 距 initDate >=365 的记录数
    count_365 = 0
    for it in Item.objects.all():
        if it.next_review_date and it.initDate:
            try:
                if (it.next_review_date - it.initDate).days >= 365:
                    count_365 += 1
            except Exception:
                pass
    print(f"Items whose next_review_date - initDate >= 365: {count_365}")

if __name__ == '__main__':
    inspect()
