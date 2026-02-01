#!/usr/bin/env python
"""
生成模拟运行后详细报告：
- 按 Item (名称以 sim_word_ 开头) 列出 initDate、current_interval、next_review_date、proficiency、needs_extra_review、unfamiliar_history 等。
- 统计总体数据并输出为 JSON 与 Markdown 报告文件。
"""
import os
import django
import json
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EbbinghausAnywhere.settings')
django.setup()

from EAW.models import Item

OUT_JSON = 'simulate_report.json'
OUT_MD = 'simulate_report.md'

def collect():
    items = Item.objects.filter(item__startswith='sim_word_')
    total = items.count()
    data = {'total': total, 'items': []}
    finished = 0
    total_no = 0
    for it in items:
        uh = it.unfamiliar_history or []
        no_count = len(uh)
        total_no += no_count
        finished_flag = (it.current_interval == 180)
        if finished_flag:
            finished += 1
        rec = {
            'id': it.id,
            'item': it.item,
            'initDate': str(it.initDate) if it.initDate else None,
            'inputDate': str(it.inputDate) if it.inputDate else None,
            'current_interval': it.current_interval,
            'next_review_date': str(it.next_review_date) if it.next_review_date else None,
            'proficiency': it.get_proficiency_display() if hasattr(it, 'get_proficiency_display') else str(it.proficiency),
            'needs_extra_review': bool(it.needs_extra_review),
            'unfamiliar_count': no_count,
            'unfamiliar_history': uh,
            'finished': finished_flag,
        }
        data['items'].append(rec)

    data['summary'] = {
        'total_items': total,
        'finished': finished,
        'total_no_records': total_no,
    }
    return data

def write_files(data):
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Markdown
    lines = []
    lines.append('# 模拟运行详细报告')
    lines.append(f'- 生成日期: {date.today().isoformat()}')
    lines.append('')
    s = data.get('summary', {})
    lines.append('## 概要')
    lines.append(f'- 总条目: {s.get("total_items")}')
    lines.append(f'- 到达最终间隔 (Day180) 的条目数: {s.get("finished")}')
    lines.append(f'- 总计记录的 NO 次数: {s.get("total_no_records")}')
    lines.append('')
    lines.append('## 各条目详情')
    for it in data['items']:
        lines.append(f'### {it["item"]} (id={it["id"]})')
        lines.append(f'- initDate: {it["initDate"]}  \n- inputDate: {it["inputDate"]}  \n- current_interval: {it["current_interval"]}  \n- next_review_date: {it["next_review_date"]}  \n- proficiency: {it["proficiency"]}  \n- needs_extra_review: {it["needs_extra_review"]}  \n- unfamiliar_count: {it["unfamiliar_count"]}  \n- finished: {it["finished"]}')
        lines.append('- unfamiliar_history:')
        if it['unfamiliar_history']:
            for r in it['unfamiliar_history']:
                lines.append(f'  - {r}')
        else:
            lines.append('  - (none)')
        lines.append('')

    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def main():
    data = collect()
    write_files(data)
    print(f'Report written to {OUT_JSON} and {OUT_MD}')

if __name__ == '__main__':
    main()
