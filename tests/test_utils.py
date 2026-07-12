"""
tests/test_utils.py
--------------------
Unit tests for utils/validators.py and utils/text_utils.py.

Run with:
    pytest tests/ -v
"""

import pytest

from utils.text_utils import compute_text_stats, percentage_change
from utils.validators import ValidationError, validate_input_text, validate_temperature


class TestValidateInputText:
    def test_valid_text_is_returned_stripped(self):
        assert validate_input_text("  hello world  ", 100) == "hello world"

    def test_empty_string_raises(self):
        with pytest.raises(ValidationError):
            validate_input_text("", 100)

    def test_whitespace_only_raises(self):
        with pytest.raises(ValidationError):
            validate_input_text("     \n\t  ", 100)

    def test_none_raises(self):
        with pytest.raises(ValidationError):
            validate_input_text(None, 100)  # type: ignore[arg-type]

    def test_too_long_raises(self):
        with pytest.raises(ValidationError):
            validate_input_text("a" * 50, max_characters=10)

    def test_exactly_at_limit_is_allowed(self):
        text = "a" * 10
        assert validate_input_text(text, max_characters=10) == text


class TestValidateTemperature:
    def test_valid_temperatures(self):
        assert validate_temperature(0.0) == 0.0
        assert validate_temperature(0.5) == 0.5
        assert validate_temperature(1.0) == 1.0

    def test_below_range_raises(self):
        with pytest.raises(ValidationError):
            validate_temperature(-0.1)

    def test_above_range_raises(self):
        with pytest.raises(ValidationError):
            validate_temperature(1.1)


class TestComputeTextStats:
    def test_basic_counts(self):
        stats = compute_text_stats("hello world")
        assert stats.word_count == 2
        assert stats.character_count == 11
        assert stats.character_count_no_spaces == 10

    def test_empty_text(self):
        stats = compute_text_stats("")
        assert stats.word_count == 0
        assert stats.character_count == 0
        assert stats.character_count_no_spaces == 0

    def test_multiline_text(self):
        stats = compute_text_stats("line one\nline two")
        assert stats.word_count == 4


class TestPercentageChange:
    def test_increase(self):
        assert percentage_change(10, 15) == 50.0

    def test_decrease(self):
        assert percentage_change(10, 5) == -50.0

    def test_no_change(self):
        assert percentage_change(10, 10) == 0.0

    def test_zero_original_avoids_division_error(self):
        assert percentage_change(0, 10) == 0.0
