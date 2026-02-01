#!/usr/bin/env python
"""
数据迁移脚本：为现有的Item设置新的复习字段
根据当前的initDate和inputDate计算应有的复习进度
"""
import os
import django
from datetime import datetime, timedelta

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EbbinghausAnywhere.settings')
django.setup()

from EAW.models import Item

# 艾宾浩斯复习间隔（天数）
REVIEW_INTERVALS = [0, 1, 2, 4, 7, 15, 30, 90, 180]

def migrate_items():
    """迁移所有现有的Item"""
    items = Item.objects.all()
    total = items.count()
    print(f"找到 {total} 个待迁移的Item...")
    
    updated = 0
    for item in items:
        # 如果已经设置了next_review_date，跳过
        if item.next_review_date:
            continue
            
        # 计算天数差异
        if item.initDate and item.inputDate:
            days_since_init = (datetime.today().date() - item.initDate).days
            
            # 根据天数确定应该处于哪个复习间隔
            current_interval = 0
            for i, interval in enumerate(REVIEW_INTERVALS):
                if days_since_init >= interval:
                    current_interval = i
                else:
                    break
            
            # 设置新字段
            item.current_interval = current_interval
            
            # 计算下次复习日期
            if current_interval < len(REVIEW_INTERVALS) - 1:
                # 还未到最后一个间隔，计算下次复习日期
                next_interval_days = REVIEW_INTERVALS[current_interval]
                item.next_review_date = item.initDate + timedelta(days=next_interval_days)
            else:
                # 已经到了最后一个间隔（Day 365），设置为一年后
                item.next_review_date = item.initDate + timedelta(days=365)
            
            # 初始化其他字段
            item.unfamiliar_history = []
            item.needs_extra_review = False
            item.extra_review_since = None
            
            item.save()
            updated += 1
            
            if updated % 100 == 0:
                print(f"已更新 {updated}/{total} 个Item...")
        else:
            # 如果没有initDate，使用inputDate作为起始日期
            if item.inputDate:
                item.current_interval = 0
                item.next_review_date = item.inputDate
                item.unfamiliar_history = []
                item.needs_extra_review = False
                item.extra_review_since = None
                item.save()
                updated += 1
    
    print(f"迁移完成！共更新了 {updated} 个Item。")

if __name__ == '__main__':
    migrate_items()
