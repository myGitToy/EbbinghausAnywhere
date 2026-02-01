#!/usr/bin/env python
"""
脚本：修复数据库中 `current_interval` 超出新最大索引的 Item 并重算 `next_review_date`。
用法：在项目根目录下运行：
  conda run -p ./.conda --no-capture-output python fix_intervals.py
"""
import os
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EbbinghausAnywhere.settings')
django.setup()

from EAW.models import Item

INTERVALS = [0, 1, 2, 4, 7, 15, 30, 90, 180]
MAX_IDX = len(INTERVALS) - 1

MAX_DAY = INTERVALS[MAX_IDX]

def fix_items():
    items = Item.objects.all()
    total = items.count()
    print(f"检查 {total} 个 Item，修复 current_interval > {MAX_IDX} 的记录...")

    updated = 0
    for item in items:
        changed = False

        # 如果 current_interval 超出新最大索引，裁剪并重算 next_review_date
        if item.current_interval is not None:
            # 如果 current_interval 存的是索引（大概率为整数索引），则把它转换为天数值
            if isinstance(item.current_interval, int) and item.current_interval > MAX_IDX:
                old = item.current_interval
                item.current_interval = MAX_DAY
                base_date = item.initDate or item.inputDate
                if base_date:
                    item.next_review_date = base_date + timedelta(days=item.current_interval)
                else:
                    item.next_review_date = datetime.today().date() + timedelta(days=item.current_interval)
                changed = True
                print(f"Item(id={item.id}) current_interval {old} -> {item.current_interval}, next_review_date set to {item.next_review_date}")
            # 如果 current_interval 是索引但在范围内，转换为天数
            elif isinstance(item.current_interval, int) and 0 <= item.current_interval <= MAX_IDX:
                old = item.current_interval
                item.current_interval = INTERVALS[old]
                base_date = item.initDate or item.inputDate
                if base_date:
                    item.next_review_date = base_date + timedelta(days=item.current_interval)
                else:
                    item.next_review_date = datetime.today().date() + timedelta(days=item.current_interval)
                changed = True
                print(f"Item(id={item.id}) current_interval index {old} -> day {item.current_interval}, next_review_date set to {item.next_review_date}")
            else:
                item.next_review_date = datetime.today().date() + timedelta(days=INTERVALS[item.current_interval])
            changed = True
            print(f"Item(id={item.id}) current_interval {old} -> {item.current_interval}, next_review_date set to {item.next_review_date}")

        # 额外安全检查：若 next_review_date 距 initDate >= 365 天，说明以前是 Day365，需要修正为 Day180
        elif item.next_review_date and item.initDate:
            try:
                delta_days = (item.next_review_date - item.initDate).days
                if delta_days >= 365:
                    old_date = item.next_review_date
                    item.current_interval = MAX_DAY
                    item.next_review_date = item.initDate + timedelta(days=item.current_interval)
                    changed = True
                    print(f"Item(id={item.id}) next_review_date {old_date} -> {item.next_review_date} (修正为 Day{item.current_interval})")
            except Exception:
                pass

        if changed:
            item.save()
            updated += 1

    print(f"修复完成，共更新 {updated} 个 Item。")

if __name__ == '__main__':
    fix_items()
