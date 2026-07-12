"""
utils/validators.py
--------------------
Pure input-validation helpers, kept free of any Streamlit or network
dependency so they can be unit tested in isolation and reused if the
UI layer is ever swapped (e.g. for a FastAPI backend later).
"""

from __future__ import annotations


class ValidationError(Exception):
    """Raised when user-supplied input fails validation."""


def validate_input_text(text: str, max_characters: int) -> str:
    """Validates and normalizes the text the user wants converted.

    Args:
        text: Raw text from the Streamlit text area.
        max_characters: Upper bound on allowed input length.

    Returns:
        The stripped, validated text.

    Raises:
        ValidationError: if the text is empty/whitespace-only, or
            exceeds `max_characters`.
    """
    if text is None:
        raise ValidationError("Please enter some text to convert.")

    stripped = text.strip()

    if not stripped:
        raise ValidationError("Please enter some text to convert.")

    if len(stripped) > max_characters:
        raise ValidationError(
            f"Input is too long ({len(stripped)} characters). "
            f"Please limit input to {max_characters} characters."
        )

    return stripped


def validate_temperature(temperature: float) -> float:
    """Ensures the creativity/temperature slider value is within bounds."""
    if temperature < 0.0 or temperature > 1.0:
        raise ValidationError("Creativity must be between 0.0 and 1.0.")
    return temperature
