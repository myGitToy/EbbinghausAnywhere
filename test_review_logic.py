#!/usr/bin/env python
"""
测试复习逻辑的日期计算
"""
from datetime import datetime, timedelta

intervals = [0, 1, 2, 4, 7, 15, 30, 90, 180]

def test_yes_logic():
    """测试点击YES的日期计算"""
    print("=== 测试点击YES的日期计算 ===")
    review_date = datetime(2026, 2, 1).date()
    
    for i in range(len(intervals) - 1):
        current_interval = intervals[i]
        next_interval = intervals[i + 1]
        days_until_next = next_interval - current_interval
        next_review_date = review_date + timedelta(days=days_until_next)
        
        print(f"Day {current_interval} → Day {next_interval}: "
              f"今天({review_date}) + {days_until_next}天 = {next_review_date}")
    
    print()

def test_specific_case():
    """测试具体案例"""
    print("=== 测试具体案例 ===")
    
    # 案例1: 2月1日创建单词，Day 0
    input_date = datetime(2026, 2, 1).date()
    current_interval = 0
    print(f"2月1日: 创建单词，current_interval=0, next_review_date={input_date}")
    
    # 2月1日点YES，Day 0 → Day 1
    review_date1 = datetime(2026, 2, 1).date()
    next_interval1 = 1
    days_until_next1 = next_interval1 - current_interval
    next_review_date1 = review_date1 + timedelta(days=days_until_next1)
    print(f"2月1日点YES: Day 0 → Day 1, next_review_date={next_review_date1} (应该是2月2日)")
    
    # 2月2日点YES，Day 1 → Day 2
    review_date2 = datetime(2026, 2, 2).date()
    current_interval2 = 1
    next_interval2 = 2
    days_until_next2 = next_interval2 - current_interval2
    next_review_date2 = review_date2 + timedelta(days=days_until_next2)
    print(f"2月2日点YES: Day 1 → Day 2, next_review_date={next_review_date2} (应该是2月3日)")
    
    # 2月3日点YES，Day 2 → Day 4
    review_date3 = datetime(2026, 2, 3).date()
    current_interval3 = 2
    next_interval3 = 4
    days_until_next3 = next_interval3 - current_interval3
    next_review_date3 = review_date3 + timedelta(days=days_until_next3)
    print(f"2月3日点YES: Day 2 → Day 4, next_review_date={next_review_date3} (应该是2月5日)")
    
    # 2月5日点YES，Day 4 → Day 7
    review_date4 = datetime(2026, 2, 5).date()
    current_interval4 = 4
    next_interval4 = 7
    days_until_next4 = next_interval4 - current_interval4
    next_review_date4 = review_date4 + timedelta(days=days_until_next4)
    print(f"2月5日点YES: Day 4 → Day 7, next_review_date={next_review_date4} (应该是2月8日)")
    
    print()

if __name__ == '__main__':
    test_yes_logic()
    test_specific_case()
