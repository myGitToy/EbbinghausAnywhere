# study-hub OTT 桥接测试（Phase 5.3）：bridge 换票/影子用户/失败分支 + 服务间全局登出 + CORS 收紧

from unittest import mock

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase


def fake_consume(payload=None, reason=None):
    """构造 consume_ott 的替身返回值"""
    return payload, reason


class SsoBridgeTests(TestCase):
    def _get(self, ott='t-1234567890123456789'):
        with mock.patch('EAW.sso.consume_ott') as consume:
            consume.return_value = (
                {'userId': 'central-u1', 'username': 'family-parent'},
                None,
            )
            return self.client.get(f'/sso/bridge/?ott={ott}')

    def test_成功_新用户建影子并登录跳首页(self):
        resp = self._get()
        self.assertRedirects(resp, '/', fetch_redirect_response=False)
        user = User.objects.get(username='family-parent')
        self.assertFalse(user.has_usable_password())  # 影子用户：占位不可用密码
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)  # 已建 Django 会话

    def test_成功_同名已有用户直接登录不新建(self):
        User.objects.create_user(username='family-parent', password='local-pass-123')
        before = User.objects.count()
        resp = self._get()
        self.assertRedirects(resp, '/', fetch_redirect_response=False)
        self.assertEqual(User.objects.count(), before)  # 不新建
        # 已有用户密码不被影子化覆盖
        self.assertTrue(User.objects.get(username='family-parent').has_usable_password())

    def test_换票失败_跳登录页带原因(self):
        for reason in ('rejected', 'invalid', 'unconfigured', 'unreachable'):
            with self.subTest(reason=reason):
                with mock.patch('EAW.sso.consume_ott') as consume:
                    consume.return_value = (None, reason)
                    resp = self.client.get('/sso/bridge/?ott=t-1234567890123456789')
                self.assertRedirects(resp, f'/accounts/login/?sso={reason}', fetch_redirect_response=False)

    def test_缺ott参数_按invalid处理(self):
        with mock.patch('EAW.sso.consume_ott') as consume:
            consume.return_value = (None, 'invalid')
            resp = self.client.get('/sso/bridge/')
        self.assertRedirects(resp, '/accounts/login/?sso=invalid', fetch_redirect_response=False)


class SsoLogoutTests(TestCase):
    SECRET = 'unit-test-secret-0000000000'

    def _post(self, body, username_for_session=None):
        if username_for_session:
            user = User.objects.create_user(username=username_for_session, password='local-pass-123')
            self.client.force_login(user)  # 建一个真实 session
            self.client.logout()  # 客户端登出不影响已存在的服务端 session 记录
            self.client.force_login(user)
        with mock.patch('EAW.sso.study_hub_secret', return_value=self.SECRET):
            return self.client.post('/sso/logout/', data=body, content_type='application/json')

    def test_正确secret_删除该用户全部会话(self):
        user = User.objects.create_user(username='family-parent', password='local-pass-123')
        self.client.force_login(user)
        resp = self._post({'appSecret': self.SECRET, 'username': 'family-parent'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['deleted'], 1)
        # 会话已被清：再访问需登录
        from django.contrib.sessions.models import Session
        self.assertFalse(Session.objects.filter().exists())

    def test_错误secret_403(self):
        resp = self._post({'appSecret': 'wrong-secret-000000000', 'username': 'family-parent'})
        self.assertEqual(resp.status_code, 403)

    def test_用户不存在_返回deleted0(self):
        resp = self._post({'appSecret': self.SECRET, 'username': 'ghost'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['deleted'], 0)

    def test_GET拒绝(self):
        resp = self.client.get('/sso/logout/')
        self.assertEqual(resp.status_code, 405)


class CorsTightenedTests(TestCase):
    def test_CORS已收紧为白名单且门户在列(self):
        self.assertFalse(settings.CORS_ALLOW_ALL_ORIGINS)
        self.assertIn('http://192.168.1.155:8092', settings.CORS_ALLOWED_ORIGINS)
        self.assertIn('http://192.168.1.155:8092', settings.CSRF_TRUSTED_ORIGINS)
