from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date, timedelta

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
