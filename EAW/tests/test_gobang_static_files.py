"""
五子棋静态文件测试

测试五子棋游戏的静态文件配置：
1. 验证静态文件目录结构
2. 验证静态文件是否存在
3. 验证 Django 静态文件系统能否正确找到文件
4. 验证 index.html 中的资源路径是否正确
"""

import os
from pathlib import Path
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
import json


class GobangStaticFilesTest(TestCase):
    """测试五子棋静态文件配置"""

    def setUp(self):
        """设置测试环境"""
        self.gobang_dir = Path(settings.BASE_DIR) / 'static' / 'gobang'
        self.gobang_static_dir = self.gobang_dir / 'static'
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = Client()

    def test_gobang_directory_exists(self):
        """测试五子棋目录是否存在"""
        self.assertTrue(
            self.gobang_dir.exists(),
            "五子棋目录不存在：static/gobang/"
        )
        self.assertTrue(
            self.gobang_static_dir.exists(),
            "五子棋静态文件目录不存在：static/gobang/static/"
        )

    def test_gobang_index_html_exists(self):
        """测试 index.html 是否存在"""
        index_file = self.gobang_dir / 'index.html'
        self.assertTrue(
            index_file.exists(),
            "五子棋入口文件不存在：static/gobang/index.html"
        )

    def test_gobang_js_files_exist(self):
        """测试 JavaScript 文件是否存在"""
        js_dir = self.gobang_static_dir / 'js'

        self.assertTrue(
            js_dir.exists(),
            "JavaScript 目录不存在：static/gobang/static/js/"
        )

        # 检查主要的 JS 文件
        required_js_files = [
            'main.dc7695ae.js',
            '453.afcdadab.chunk.js',
            '536.6ba76015.chunk.js',
            '686.d0204ed7.chunk.js'
        ]

        for js_file in required_js_files:
            file_path = js_dir / js_file
            self.assertTrue(
                file_path.exists(),
                f"JavaScript 文件不存在：static/gobang/static/js/{js_file}"
            )
            # 验证文件不为空
            self.assertGreater(
                file_path.stat().st_size,
                0,
                f"JavaScript 文件为空：static/gobang/static/js/{js_file}"
            )

    def test_gobang_css_files_exist(self):
        """测试 CSS 文件是否存在"""
        css_dir = self.gobang_static_dir / 'css'

        self.assertTrue(
            css_dir.exists(),
            "CSS 目录不存在：static/gobang/static/css/"
        )

        # 检查主要的 CSS 文件
        required_css_files = [
            'main.24ac5095.css'
        ]

        for css_file in required_css_files:
            file_path = css_dir / css_file
            self.assertTrue(
                file_path.exists(),
                f"CSS 文件不存在：static/gobang/static/css/{css_file}"
            )
            # 验证文件不为空
            self.assertGreater(
                file_path.stat().st_size,
                0,
                f"CSS 文件为空：static/gobang/static/css/{css_file}"
            )

    def test_gobang_media_files_exist(self):
        """测试媒体文件是否存在"""
        media_dir = self.gobang_static_dir / 'media'

        self.assertTrue(
            media_dir.exists(),
            "媒体文件目录不存在：static/gobang/static/media/"
        )

        # 检查背景图片
        bg_file = media_dir / 'bg.5f5d204f7a75ee4fe91c.jpg'
        self.assertTrue(
            bg_file.exists(),
            "背景图片不存在：static/gobang/static/media/bg.5f5d204f7a75ee4fe91c.jpg"
        )

    def test_asset_manifest_exists(self):
        """测试 asset-manifest.json 是否存在"""
        manifest_file = self.gobang_dir / 'asset-manifest.json'

        self.assertTrue(
            manifest_file.exists(),
            "资产清单文件不存在：static/gobang/asset-manifest.json"
        )

        # 验证 JSON 格式是否正确
        try:
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            self.assertIn('files', manifest, "asset-manifest.json 缺少 'files' 字段")
            self.assertIn('entrypoints', manifest, "asset-manifest.json 缺少 'entrypoints' 字段")

        except json.JSONDecodeError as e:
            self.fail(f"asset-manifest.json 格式错误：{e}")

    def test_index_html_uses_relative_paths(self):
        """测试 index.html 是否使用相对路径"""
        index_file = self.gobang_dir / 'index.html'

        with open(index_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否使用相对路径（应该包含 ./static/ 而不是 /static/）
        self.assertIn(
            './static/js/',
            content,
            "index.html 应该使用相对路径 './static/js/' 而不是绝对路径 '/static/js/'"
        )
        self.assertIn(
            './static/css/',
            content,
            "index.html 应该使用相对路径 './static/css/' 而不是绝对路径 '/static/css/'"
        )

        # 检查是否包含绝对路径（不应该包含）
        self.assertNotIn(
            'src="/static/',
            content,
            "index.html 不应该使用绝对路径 'src=\"/static/\"'"
        )

    def test_django_staticfiles_finds_gobang_files(self):
        """测试 Django 静态文件系统能否找到五子棋文件"""
        from django.contrib.staticfiles import finders

        # 测试能否找到主要的 JS 文件
        result = finders.find('gobang/static/js/main.dc7695ae.js')
        self.assertIsNotNone(
            result,
            "Django 静态文件系统找不到：gobang/static/js/main.dc7695ae.js"
        )

        # 测试能否找到主要的 CSS 文件
        result = finders.find('gobang/static/css/main.24ac5095.css')
        self.assertIsNotNone(
            result,
            "Django 静态文件系统找不到：gobang/static/css/main.24ac5095.css"
        )

        # 测试能否找到媒体文件
        result = finders.find('gobang/static/media/bg.5f5d204f7a75ee4fe91c.jpg')
        self.assertIsNotNone(
            result,
            "Django 静态文件系统找不到：gobang/static/media/bg.5f5d204f7a75ee4fe91c.jpg"
        )


class GobangViewTest(TestCase):
    """测试五子棋视图功能"""

    def setUp(self):
        """设置测试环境"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        from EAW.models import UserPoints
        UserPoints.objects.create(user=self.user)
        self.client = Client()

    def test_gobang_page_requires_login(self):
        """测试五子棋页面需要登录"""
        response = self.client.get('/gobang/')
        self.assertNotEqual(
            response.status_code,
            200,
            "未登录用户不应该能直接访问五子棋页面"
        )
        # 应该重定向到登录页面
        self.assertEqual(
            response.status_code,
            302,
            "未登录用户应该被重定向到登录页面"
        )

    def test_gobang_page_accessible_when_logged_in(self):
        """测试登录用户可以访问五子棋页面"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/gobang/')

        self.assertEqual(
            response.status_code,
            200,
            "登录用户应该能访问五子棋页面"
        )

        # 检查是否包含 iframe
        self.assertContains(
            response,
            '<iframe',
            msg_prefix="五子棋页面应该包含 iframe 标签"
        )

        # 检查 iframe 是否指向正确的路径
        self.assertContains(
            response,
            'src="/static/gobang/index.html"',
            msg_prefix="iframe 应该指向 /static/gobang/index.html"
        )

    def test_gobang_no_points_deduction(self):
        """测试测试期间不扣除积分"""
        from EAW.models import UserPoints

        self.client.login(username='testuser', password='testpass123')

        # 获取初始积分
        initial_points = UserPoints.objects.get(user=self.user).current_points

        # 访问五子棋页面
        response = self.client.get('/gobang/')
        self.assertEqual(response.status_code, 200)

        # 检查积分没有被扣除
        final_points = UserPoints.objects.get(user=self.user).current_points
        self.assertEqual(
            initial_points,
            final_points,
            "测试期间不应该扣除积分"
        )


class GobangStaticFilesIntegrationTest(StaticLiveServerTestCase):
    """五子棋静态文件集成测试（测试实际HTTP访问）"""

    def setUp(self):
        """设置测试环境"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        from EAW.models import UserPoints
        UserPoints.objects.create(user=self.user)

    def test_static_files_accessible_via_http(self):
        """测试静态文件可以通过 HTTP 访问"""
        import requests

        # 测试主 JS 文件
        url = f'{self.live_server_url}/static/gobang/static/js/main.dc7695ae.js'
        response = requests.get(url)
        self.assertEqual(
            response.status_code,
            200,
            f"无法通过 HTTP 访问：{url}"
        )
        self.assertGreater(
            len(response.content),
            1000,
            "JS 文件内容过小，可能不完整"
        )

        # 测试主 CSS 文件
        url = f'{self.live_server_url}/static/gobang/static/css/main.24ac5095.css'
        response = requests.get(url)
        self.assertEqual(
            response.status_code,
            200,
            f"无法通过 HTTP 访问：{url}"
        )

        # 测试背景图片
        url = f'{self.live_server_url}/static/gobang/static/media/bg.5f5d204f7a75ee4fe91c.jpg'
        response = requests.get(url)
        self.assertEqual(
            response.status_code,
            200,
            f"无法通过 HTTP 访问：{url}"
        )

    def test_gobang_index_html_accessible(self):
        """测试五子棋 index.html 可以通过 HTTP 访问"""
        import requests

        url = f'{self.live_server_url}/static/gobang/index.html'
        response = requests.get(url)
        self.assertEqual(
            response.status_code,
            200,
            f"无法通过 HTTP 访问：{url}"
        )

        # 检查内容是否包含 React 根节点
        self.assertIn(
            '<div id="root"></div>',
            response.text,
            "index.html 应该包含 React 根节点"
        )


# 运行测试的辅助函数
def run_gobang_tests():
    """
    运行五子棋静态文件测试的辅助函数

    使用方法：
    python manage.py test EAW.tests.test_gobang_static_files
    """
    print("五子棋静态文件测试")
    print("=" * 60)
    print("\n测试项目：")
    print("1. 目录结构验证")
    print("2. 文件存在性检查")
    print("3. Django 静态文件系统集成")
    print("4. HTTP 访问测试")
    print("5. 视图功能测试")
    print("\n运行命令：")
    print("  ./.conda/python.exe manage.py test EAW.tests.test_gobang_static_files")
    print("\n或运行特定测试类：")
    print("  ./.conda/python.exe manage.py test EAW.tests.test_gobang_static_files.GobangStaticFilesTest")
    print("  ./.conda/python.exe manage.py test EAW.tests.test_gobang_static_files.GobangViewTest")
    print("  ./.conda/python.exe manage.py test EAW.tests.test_gobang_static_files.GobangStaticFilesIntegrationTest")


if __name__ == '__main__':
    run_gobang_tests()
