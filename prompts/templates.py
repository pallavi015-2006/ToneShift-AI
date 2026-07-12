"""
prompts/templates.py
---------------------
All prompt-engineering logic lives here, isolated from both the UI
(app.py) and the LLM transport layer (llm/*). This makes prompts easy
to inspect, unit test, and demonstrate independently during a viva —
you can show a grader exactly what is sent to the model without
touching networking code.

Two prompts are built per request:
    1. A system prompt: defines the assistant's role, the tone
       definition, and strict output-format rules (no preamble, no
       meta-commentary, just the rewritten text).
    2. A user prompt: contains the length instruction and the original
       text to transform.
"""

from __future__ import annotations

from config import RESPONSE_LENGTH_MAP

# Short, precise definitions for each tone keep the model's rewrites
# consistent and reduce ambiguity (e.g. "Professional" vs "Formal").
TONE_DEFINITIONS: dict[str, str] = {
    "Formal": (
        "Use formal register: precise vocabulary, complete sentences, no "
        "contractions or slang, respectful and impersonal phrasing."
    ),
    "Friendly": (
        "Use a warm, approachable, conversational tone as if speaking to "
        "a friend, while keeping the meaning intact."
    ),
    "Professional": (
        "Use clear, polished workplace language suitable for colleagues "
        "or clients: confident, courteous, and free of slang."
    ),
    "Casual": (
        "Use relaxed, everyday language with contractions, as if texting "
        "or chatting informally."
    ),
    "Academic": (
        "Use scholarly language: objective, precise, structured, and "
        "appropriate for an academic paper or research context."
    ),
    "Persuasive": (
        "Use compelling, confident language designed to convince the "
        "reader and motivate action, without being manipulative."
    ),
    "Funny": (
        "Add light humor, wit, or playful phrasing while preserving the "
        "original message's core meaning."
    ),
    "Motivational": (
        "Use uplifting, energetic, encouraging language that inspires "
        "the reader to take positive action."
    ),
    "Child Friendly": (
        "Use simple words, short sentences, and a gentle, cheerful tone "
        "appropriate for young children."
    ),
    "Email": (
        "Format as a polished professional email with an appropriate "
        "greeting and sign-off, clear paragraphs, and courteous tone."
    ),
    "Social Media": (
        "Use punchy, engaging, concise language suitable for a social "
        "media post; light use of emojis is acceptable if natural."
    ),
    "Customer Support": (
        "Use empathetic, solution-oriented, professional language typical "
        "of a helpful customer support representative."
    ),
}


def build_system_prompt(tone: str) -> str:
    """Builds the system-level instruction that fixes the assistant's role.

    Args:
        tone: One of config.SUPPORTED_TONES.

    Raises:
        ValueError: if `tone` is not a recognized tone.
    """
    if tone not in TONE_DEFINITIONS:
        raise ValueError(f"Unsupported tone: {tone!r}")

    tone_rule = TONE_DEFINITIONS[tone]

    return (
        "You are ToneShift, an expert writing assistant that rewrites text "
        "in a requested tone while strictly preserving the original "
        "meaning, facts, and intent.\n\n"
        f"Target tone: {tone}.\n"
        f"Tone guidance: {tone_rule}\n\n"
        "Strict output rules:\n"
        "- Output ONLY the rewritten text.\n"
        "- Do not add explanations, labels, quotation marks, or preambles "
        "such as 'Here is the rewritten text:'.\n"
        "- Do not invent new facts, names, or details not present in the "
        "original text.\n"
        "- Preserve the original language of the text (do not translate).\n"
        "- Preserve any lists, line breaks, or structure that are "
        "meaningful to the message, adapting formatting only as needed "
        "for the target tone."
    )


def build_user_prompt(original_text: str, response_length: str) -> str:
    """Builds the user-level instruction containing the task and the text.

    Args:
        original_text: The raw text supplied by the end user.
        response_length: One of the keys in config.RESPONSE_LENGTH_MAP
            ("Short", "Medium", "Long").

    Raises:
        ValueError: if `response_length` is not recognized.
    """
    if response_length not in RESPONSE_LENGTH_MAP:
        raise ValueError(f"Unsupported response length: {response_length!r}")

    length_rule = RESPONSE_LENGTH_MAP[response_length]

    return (
        f"Length guidance: {length_rule}\n\n"
        "Rewrite the following text according to the tone and length "
        "guidance above:\n"
        "---\n"
        f"{original_text}\n"
        "---"
    )
