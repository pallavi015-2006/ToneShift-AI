"""
utils/text_utils.py
--------------------
Small, dependency-free text utilities used to compute the meta info
(word/character counts) shown alongside the conversion results.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextStats:
    """Basic statistics computed for a piece of text."""

    word_count: int
    character_count: int
    character_count_no_spaces: int


def compute_text_stats(text: str) -> TextStats:
    """Computes word and character counts for the given text.

    Word counting splits on whitespace, which is a simple and
    predictable heuristic appropriate for a comparison metric (it does
    not need to be linguistically perfect, only consistent between the
    original and converted text).
    """
    words = text.split()
    return TextStats(
        word_count=len(words),
        character_count=len(text),
        character_count_no_spaces=len(text.replace(" ", "").replace("\n", "")),
    )


def percentage_change(original: int, converted: int) -> float:
    """Returns the percentage change from `original` to `converted`.

    Returns 0.0 if `original` is 0 to avoid a division-by-zero error.
    """
    if original == 0:
        return 0.0
    return round(((converted - original) / original) * 100, 1)
