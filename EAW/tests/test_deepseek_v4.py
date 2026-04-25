"""
Tests for DeepSeek V4 Flash upgrade.
Validates: default model, thinking disabled, temperature preserved, legacy model mapping.
"""
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.contrib.auth.models import User

from EAW.models import DeepSeekConfig


LEGACY_MODEL = "deepseek-chat"
NEW_MODEL = "deepseek-v4-flash"


class TestDeepSeekRequestConstruction(TestCase):
    """Verify API kwargs built by call_deepseek_api."""

    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="pass")

    @patch("EAW.deepseek.OpenAI")
    @patch("EAW.deepseek.DEEPSEEK_API_KEY", "sk-test-key")
    def test_default_model_is_v4_flash(self, mock_openai_cls):
        from EAW.deepseek import call_deepseek_api

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"uk_phonetic":"/a/","us_phonetic":"/a/","meaning":"test","example_sentences":[]}'
        mock_client.chat.completions.create.return_value = mock_response

        call_deepseek_api("apple", config=None, user=None)

        call_kwargs = mock_client.chat.completions.create.call_args
        self.assertEqual(call_kwargs.kwargs.get("model"), NEW_MODEL)

    @patch("EAW.deepseek.OpenAI")
    @patch("EAW.deepseek.DEEPSEEK_API_KEY", "sk-test-key")
    def test_thinking_disabled_in_extra_body(self, mock_openai_cls):
        from EAW.deepseek import call_deepseek_api

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"uk_phonetic":"/a/","us_phonetic":"/a/","meaning":"test","example_sentences":[]}'
        mock_client.chat.completions.create.return_value = mock_response

        call_deepseek_api("apple", config=None, user=None)

        call_kwargs = mock_client.chat.completions.create.call_args
        self.assertEqual(
            call_kwargs.kwargs.get("extra_body"),
            {"thinking": {"type": "disabled"}},
        )

    @patch("EAW.deepseek.OpenAI")
    @patch("EAW.deepseek.DEEPSEEK_API_KEY", "sk-test-key")
    def test_temperature_preserved_in_non_thinking_mode(self, mock_openai_cls):
        from EAW.deepseek import call_deepseek_api

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"uk_phonetic":"/a/","us_phonetic":"/a/","meaning":"test","example_sentences":[]}'
        mock_client.chat.completions.create.return_value = mock_response

        call_deepseek_api("apple", config=None, user=None)

        call_kwargs = mock_client.chat.completions.create.call_args
        self.assertIn("temperature", call_kwargs.kwargs)
        self.assertEqual(call_kwargs.kwargs["temperature"], 1.0)

    @patch("EAW.deepseek.OpenAI")
    @patch("EAW.deepseek.DEEPSEEK_API_KEY", "sk-test-key")
    def test_no_reasoning_effort_in_non_thinking_mode(self, mock_openai_cls):
        from EAW.deepseek import call_deepseek_api

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"uk_phonetic":"/a/","us_phonetic":"/a/","meaning":"test","example_sentences":[]}'
        mock_client.chat.completions.create.return_value = mock_response

        call_deepseek_api("apple", config=None, user=None)

        call_kwargs = mock_client.chat.completions.create.call_args
        self.assertNotIn("reasoning_effort", call_kwargs.kwargs)

    @patch("EAW.deepseek.OpenAI")
    @patch("EAW.deepseek.DEEPSEEK_API_KEY", "sk-test-key")
    def test_legacy_model_mapped_to_v4_flash(self, mock_openai_cls):
        """Old deepseek-chat config should be transparently mapped to v4-flash."""
        from EAW.deepseek import call_deepseek_api

        config = DeepSeekConfig.objects.create(
            user=self.user, model=LEGACY_MODEL, temperature=1.0, is_active=True
        )

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"uk_phonetic":"/a/","us_phonetic":"/a/","meaning":"test","example_sentences":[]}'
        mock_client.chat.completions.create.return_value = mock_response

        call_deepseek_api("apple", config=config, user=self.user)

        call_kwargs = mock_client.chat.completions.create.call_args
        self.assertEqual(call_kwargs.kwargs.get("model"), NEW_MODEL)

    @patch("EAW.deepseek.OpenAI")
    @patch("EAW.deepseek.DEEPSEEK_API_KEY", "sk-test-key")
    def test_custom_temperature_from_config(self, mock_openai_cls):
        from EAW.deepseek import call_deepseek_api

        config = DeepSeekConfig.objects.create(
            user=self.user, model=NEW_MODEL, temperature=1.3, is_active=True
        )

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"uk_phonetic":"/a/","us_phonetic":"/a/","meaning":"test","example_sentences":[]}'
        mock_client.chat.completions.create.return_value = mock_response

        call_deepseek_api("apple", config=config, user=self.user)

        call_kwargs = mock_client.chat.completions.create.call_args
        self.assertEqual(call_kwargs.kwargs["temperature"], 1.3)


class TestDeepSeekConfigDefaults(TestCase):
    """Verify model defaults in Django models, forms, views."""

    def test_model_default_value(self):
        self.assertEqual(DeepSeekConfig._meta.get_field("model").default, NEW_MODEL)

    def test_new_config_uses_v4_flash(self):
        user = User.objects.create_user(username="cfg_tester", password="pass")
        config = DeepSeekConfig.objects.create(user=user)
        self.assertEqual(config.model, NEW_MODEL)
