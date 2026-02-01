from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date, timedelta
import json

from EAW.models import Item, Category


class ItemDetailScheduleTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.cat = Category.objects.create(user=self.user, name='测试')
        self.client = Client()
        self.client.login(username='testuser', password='pass')

        # 基准日期：2 天前
        self.base = date.today() - timedelta(days=2)

        # 创建 Item：current_interval=1（表示已完成第0次），unfamiliar_history 为空
        self.item = Item.objects.create(
            user=self.user,
            category=self.cat,
            item='word',
            content='释义',
            inputDate=self.base,
            initDate=self.base,
            current_interval=1,
            next_review_date=self.base + timedelta(days=1),
            unfamiliar_history=[],
        )

    def test_review_schedule_present(self):
        url = reverse('item-detail', args=[self.item.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('review_schedule', resp.context)

        schedule = resp.context['review_schedule']
        # 现在间隔列表应为 9 项
        self.assertEqual(len(schedule), 9)

        # 第一项 (idx=0) 应被视为已完成且熟悉
        first = schedule[0]
        self.assertTrue(first['completed'])
        self.assertTrue(first['familiar'])

        # 第二项 (idx=1) 尚未完成，熟悉字段应为 None
        second = schedule[1]
        self.assertFalse(second['completed'])
        self.assertIsNone(second['familiar'])

    def test_no_persists_to_next_formal_review(self):
        # 模拟在今天点击 NO
        url_no = reverse('review-feedback-no')
        payload = {'id': self.item.id, 'date': date.today().isoformat()}
        resp = self.client.post(url_no, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))

        # 刷新并检查 unfamiliar_history
        self.item.refresh_from_db()
        self.assertTrue(self.item.unfamiliar_history)
        self.assertEqual(len(self.item.unfamiliar_history), 1)

        # 到下一次（正式）复习日期，检查该条目仍在复习列表且 unfamiliar_count 保留
        next_date = date.today() + timedelta(days=1)
        url_review = reverse('review-view', args=[next_date.year, next_date.month, next_date.day])
        resp = self.client.get(url_review)
        self.assertEqual(resp.status_code, 200)
        page_list = resp.context['page_obj'].object_list
        found = [r for r in page_list if r['item'].id == self.item.id]
        self.assertTrue(found)
        self.assertEqual(found[0]['unfamiliar_count'], 1)
