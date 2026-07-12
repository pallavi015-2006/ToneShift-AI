"""
tests/test_prompts.py
----------------------
Unit tests for prompts/templates.py.

Run with:
    pytest tests/ -v
"""

import pytest

from config import SUPPORTED_TONES
from prompts.templates import TONE_DEFINITIONS, build_system_prompt, build_user_prompt


class TestBuildSystemPrompt:
    def test_all_supported_tones_have_definitions(self):
        for tone in SUPPORTED_TONES:
            assert tone in TONE_DEFINITIONS

    def test_system_prompt_contains_tone_name(self):
        prompt = build_system_prompt("Formal")
        assert "Formal" in prompt

    def test_system_prompt_contains_output_rules(self):
        prompt = build_system_prompt("Casual")
        assert "Output ONLY the rewritten text" in prompt

    def test_unsupported_tone_raises(self):
        with pytest.raises(ValueError):
            build_system_prompt("Sarcastic-But-Not-Really")


class TestBuildUserPrompt:
    def test_user_prompt_contains_original_text(self):
        prompt = build_user_prompt("Hello there", "Medium")
        assert "Hello there" in prompt

    def test_user_prompt_contains_length_guidance(self):
        prompt = build_user_prompt("Some text", "Short")
        assert "concise" in prompt.lower()

    def test_unsupported_length_raises(self):
        with pytest.raises(ValueError):
            build_user_prompt("Some text", "Extremely Long")
