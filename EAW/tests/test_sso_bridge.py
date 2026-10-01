# study-hub OTT 桥接测试：#510 证明式绑定状态机（#80）
# 覆盖：三分支到达（直登/建影子/同名冲突→绑定票）、绑定页验密/换名、票过期篡改、
# 抢先绑定竞态、影子号默认数据、服务间全局登出（userId 优先）、登录页 ?sso= 提示、CORS 收紧。

from unittest import mock

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase

from EAW.models import Category, ReviewDay, UserProfile
from EAW import sso as sso_core

HUB_USER_ID = 'central-u1'
HUB_USERNAME = 'family-parent'


def consume_ok(payload=None):
    """consume_ott 成功替身：默认返回固定门户身份"""
    return (payload or {'userId': HUB_USER_ID, 'username': HUB_USERNAME}), None


class BridgeStateMachineTests(TestCase):
    """sso_bridge 三分支状态机（airlinesim #510 decideSsoArrival 语义）"""

    def _get(self, ott='t-1234567890123456789'):
        with mock.patch('EAW.sso.consume_ott', return_value=consume_ok()):
            return self.client.get(f'/sso/bridge/?ott={ott}')

    def test_分支三_全新用户建影子号并直登(self):
        resp = self._get()
        self.assertRedirects(resp, '/', fetch_redirect_response=False)
        user = User.objects.get(username=HUB_USERNAME)
        self.assertFalse(user.has_usable_password())  # 影子号：占位不可用密码，本地登录不可用
        self.assertTrue(UserProfile.objects.filter(
            user=user, study_hub_user_id=HUB_USER_ID).exists())  # 建立即绑定
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_影子号_默认数据已初始化(self):
        """影子号与本地注册享受同等初始化（Public 组 / 默认分类 / 复习曲线）"""
        self._get()
        user = User.objects.get(username=HUB_USERNAME)
        self.assertTrue(Category.objects.filter(user=user, name='单词', is_default=True).exists())
        self.assertEqual(ReviewDay.objects.filter(user=user).count(), 9)
        self.assertTrue(user.groups.filter(name='Public').exists())

    def test_分支一_已绑定直登且改名同步(self):
        """门户改 username 后再进：仍是同一账号（profile 命中优先，本地用户名同步）"""
        user = User.objects.create_user(username='old-name', password='x')
        UserProfile.objects.create(user=user, study_hub_user_id=HUB_USER_ID)
        self._get()
        user.refresh_from_db()
        self.assertEqual(User.objects.get(username=HUB_USERNAME).pk, user.pk)  # 同一账号，未新建
        self.assertEqual(user.username, HUB_USERNAME)       # 改名同步，数据不断链
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_分支二_同名冲突_转绑定页不自动登录(self):
        """本地已有同名真实账号：绝不按名自动合并，出绑定票，不建会话"""
        User.objects.create_user(username=HUB_USERNAME, password='local-pass-123')
        resp = self._get()
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp['Location'].startswith('/sso/bind/?t='))  # 带绑定票
        self.assertNotIn('_auth_user_id', self.client.session)       # 未登录
        self.assertFalse(UserProfile.objects.exists())               # 未绑定
        # 同名真实账号密码不被触碰
        self.assertTrue(User.objects.get(username=HUB_USERNAME).has_usable_password())

    def test_换票失败_跳登录页带原因(self):
        for reason in ('rejected', 'invalid', 'unconfigured', 'unreachable'):
            with self.subTest(reason=reason):
                with mock.patch('EAW.sso.consume_ott', return_value=(None, reason)):
                    resp = self.client.get('/sso/bridge/?ott=t-1234567890123456789')
                self.assertRedirects(resp, f'/accounts/login/?sso={reason}',
                                     fetch_redirect_response=False)

    def test_缺ott参数_按invalid处理(self):
        with mock.patch('EAW.sso.consume_ott', return_value=(None, 'invalid')):
            resp = self.client.get('/sso/bridge/')
        self.assertRedirects(resp, '/accounts/login/?sso=invalid', fetch_redirect_response=False)


class BindPageTests(TestCase):
    """同名冲突绑定页：验密绑定 / 换名新建 / 票校验 / 抢先绑定竞态"""

    def _ticket(self, hub_user_id=HUB_USER_ID, username=HUB_USERNAME):
        return sso_core.sign_bind_ticket(hub_user_id, username)

    def _get(self, ticket):
        return self.client.get(f'/sso/bind/?t={ticket}')

    def _post(self, ticket, **fields):
        data = {'t': ticket}
        data.update(fields)
        return self.client.post('/sso/bind/', data)

    def test_持有效票_GET_渲染绑定页(self):
        User.objects.create_user(username=HUB_USERNAME, password='local-pass-123')
        resp = self._get(self._ticket())
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, HUB_USERNAME)
        self.assertContains(resp, 'mode', count=2)  # bind + rename 两份表单

    def test_bind模式_密码正确_绑定并登录_本地密码保留(self):
        user = User.objects.create_user(username=HUB_USERNAME, password='local-pass-123')
        resp = self._post(self._ticket(), mode='bind', password='local-pass-123')
        self.assertRedirects(resp, '/', fetch_redirect_response=False)
        self.assertTrue(UserProfile.objects.filter(
            user=user, study_hub_user_id=HUB_USER_ID).exists())
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)
        self.assertTrue(user.has_usable_password())  # 本地登录能力不因绑定受损

    def test_bind模式_密码错误_不绑定不登录(self):
        User.objects.create_user(username=HUB_USERNAME, password='local-pass-123')
        resp = self._post(self._ticket(), mode='bind', password='wrong-pass')
        self.assertEqual(resp.status_code, 200)                     # 回绑定页报错
        self.assertContains(resp, '密码不正确')
        self.assertFalse(UserProfile.objects.exists())
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_bind模式_本地账号已绑其他门户_拒绝(self):
        other = User.objects.create_user(username=HUB_USERNAME, password='local-pass-123')
        UserProfile.objects.create(user=other, study_hub_user_id='central-other')
        resp = self._post(self._ticket(), mode='bind', password='local-pass-123')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '已绑定其他门户账号')
        self.assertEqual(UserProfile.objects.get(user=other).study_hub_user_id, 'central-other')

    def test_rename模式_换名新建影子号并登录(self):
        User.objects.create_user(username=HUB_USERNAME, password='local-pass-123')
        resp = self._post(self._ticket(), mode='rename', new_username='family-parent-2')
        self.assertRedirects(resp, '/', fetch_redirect_response=False)
        new_user = User.objects.get(username='family-parent-2')
        self.assertFalse(new_user.has_usable_password())
        self.assertTrue(UserProfile.objects.filter(
            user=new_user, study_hub_user_id=HUB_USER_ID).exists())
        self.assertTrue(Category.objects.filter(user=new_user, is_default=True).exists())
        self.assertEqual(int(self.client.session['_auth_user_id']), new_user.pk)

    def test_rename模式_重名或非法用户名_拒绝(self):
        User.objects.create_user(username=HUB_USERNAME, password='local-pass-123')
        for bad in (HUB_USERNAME, 'bad name!'):
            with self.subTest(new_username=bad):
                resp = self._post(self._ticket(), mode='rename', new_username=bad)
                self.assertEqual(resp.status_code, 200)
                # 迁移 0011 自带种子 admin，排除后计数：未新建任何账号
                self.assertEqual(User.objects.exclude(username='admin').count(), 1)

    def test_票篡改_拒绝回登录页(self):
        resp = self._get('tampered-ticket-string')
        self.assertRedirects(resp, '/accounts/login/?sso=bind_invalid',
                             fetch_redirect_response=False)

    def test_票过期_拒绝回登录页(self):
        ticket = self._ticket()
        with mock.patch('EAW.sso.SSO_BIND_TICKET_TTL', -1):
            resp = self._get(ticket)
        self.assertRedirects(resp, '/accounts/login/?sso=bind_expired',
                             fetch_redirect_response=False)

    def test_抢先绑定竞态_出票后他处已完成_直接登录(self):
        """绑定过程中该门户身份已在别处绑定：不出表单，直接登录已绑定账号"""
        user = User.objects.create_user(username='already-bound', password='x')
        UserProfile.objects.create(user=user, study_hub_user_id=HUB_USER_ID)
        resp = self._get(self._ticket())
        self.assertRedirects(resp, '/', fetch_redirect_response=False)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)


class LoginNoticeTests(TestCase):
    """登录页 ?sso= 原因提示（#80：失败不再静默）"""

    def test_各原因渲染中文提示(self):
        for reason, fragment in (
            ('invalid', '令牌无效'),
            ('unreachable', '门户暂时不可达'),
            ('bind_expired', '绑定超时'),
        ):
            with self.subTest(reason=reason):
                resp = self.client.get(f'/accounts/login/?sso={reason}')
                self.assertEqual(resp.status_code, 200)
                self.assertContains(resp, fragment)

    def test_无原因参数_不渲染提示块(self):
        resp = self.client.get('/accounts/login/')
        self.assertNotContains(resp, 'alert-warning')


class SsoLogoutTests(TestCase):
    SECRET = 'unit-test-secret-0000000000'

    def _post(self, body):
        with mock.patch('EAW.sso.study_hub_secret', return_value=self.SECRET):
            return self.client.post('/sso/logout/', data=body, content_type='application/json')

    def test_正确secret_删除该用户全部会话(self):
        user = User.objects.create_user(username=HUB_USERNAME, password='local-pass-123')
        self.client.force_login(user)
        resp = self._post({'appSecret': self.SECRET, 'username': HUB_USERNAME})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['deleted'], 1)
        from django.contrib.sessions.models import Session
        self.assertFalse(Session.objects.filter().exists())

    def test_userId字段_优先于username(self):
        """带 userId 时按联邦绑定定位（username 即使指向别人也不误删）"""
        bound = User.objects.create_user(username='bound-user', password='x')
        UserProfile.objects.create(user=bound, study_hub_user_id=HUB_USER_ID)
        bystander = User.objects.create_user(username=HUB_USERNAME, password='x')
        self.client.force_login(bound)
        resp = self._post({'appSecret': self.SECRET, 'username': bystander.username,
                           'userId': HUB_USER_ID})
        self.assertEqual(resp.json()['deleted'], 1)
        from django.contrib.sessions.models import Session
        self.assertFalse(Session.objects.filter().exists())  # 删的是 bound 的会话

    def test_错误secret_403(self):
        resp = self._post({'appSecret': 'wrong-secret-000000000', 'username': HUB_USERNAME})
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
