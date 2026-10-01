# /review/<date>/ 直链行为（#81）：非 AJAX 302 回复习首页带日期，AJAX 返回片段

from django.contrib.auth.models import User
from django.test import TestCase


class ReviewViewDirectLinkTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='rev-user', password='x')

    def setUp(self):
        self.client.force_login(self.user)

    def test_直链非AJAX_302回复习首页带日期(self):
        """直链 /review/<date>/ 不再渲染无头裸片段，而是 302 到 /review/?date=…"""
        resp = self.client.get('/review/2026-10-1/')
        self.assertRedirects(resp, '/review/?date=2026-10-01&per_page=10',
                             fetch_redirect_response=False)

    def test_直链带per_page_参数保留(self):
        resp = self.client.get('/review/2026-10-1/?per_page=50')
        self.assertRedirects(resp, '/review/?date=2026-10-01&per_page=50',
                             fetch_redirect_response=False)

    def test_AJAX头_仍返回片段200(self):
        resp = self.client.get('/review/2026-10-1/',
                               headers={'x-requested-with': 'XMLHttpRequest'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Review Items', resp.content)  # review_day.html 卡片头

    def test_未登录_跳登录页(self):
        self.client.logout()
        resp = self.client.get('/review/2026-10-1/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp['Location'])
