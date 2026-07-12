"""
app.py
------
Streamlit entry point for ToneShift – AI Tone Converter.

This module is intentionally "thin": it owns UI layout and Streamlit
session state only. All business logic (prompt construction, LLM
invocation, validation, text statistics) is delegated to dedicated
modules, keeping this file readable and easy to demo/explain in a viva.

Architecture recap:
    app.py            -> UI, orchestration, session state
    config.py         -> environment/config loading, constants
    prompts/templates -> prompt engineering (system + user prompts)
    llm/base           -> provider-agnostic client interface + errors
    llm/openai_client   -> concrete OpenAI-compatible implementation
    llm/factory         -> picks the right client from Settings
    utils/validators    -> input validation
    utils/text_utils    -> word/character statistics
"""

from __future__ import annotations

import time
from datetime import datetime

import streamlit as st

from config import RESPONSE_LENGTH_MAP, SUPPORTED_TONES, settings
from llm.base import LLMClientError
from llm.factory import build_llm_client
from prompts.templates import build_system_prompt, build_user_prompt
from utils.text_utils import compute_text_stats, percentage_change
from utils.validators import ValidationError, validate_input_text, validate_temperature

# --------------------------------------------------------------------------
# Page configuration (must be the first Streamlit call)
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="ToneShift – AI Tone Converter",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------------------------------
# Styling: a small CSS layer for polish, works well in both dark/light mode
# --------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
    .toneshift-card {
        background: rgba(124, 92, 252, 0.08);
        border: 1px solid rgba(124, 92, 252, 0.25);
        border-radius: 14px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 1rem;
    }
    .toneshift-header {
        font-size: 2.1rem;
        font-weight: 800;
        margin-bottom: 0.1rem;
    }
    .toneshift-subheader {
        opacity: 0.75;
        font-size: 1.02rem;
        margin-bottom: 1.4rem;
    }
    .stat-pill {
        display: inline-block;
        padding: 0.15rem 0.7rem;
        border-radius: 999px;
        background: rgba(124, 92, 252, 0.15);
        border: 1px solid rgba(124, 92, 252, 0.35);
        font-size: 0.82rem;
        margin-right: 0.4rem;
        margin-top: 0.3rem;
    }
    div[data-testid="stTextArea"] textarea {
        border-radius: 10px;
    }
    .history-item {
        border-left: 3px solid #7C5CFC;
        padding-left: 0.7rem;
        margin-bottom: 0.8rem;
        opacity: 0.9;
        font-size: 0.85rem;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Session state initialization
# --------------------------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history: list[dict] = []
if "last_result" not in st.session_state:
    st.session_state.last_result: dict | None = None
if "input_text" not in st.session_state:
    st.session_state.input_text = ""


# --------------------------------------------------------------------------
# Sidebar: configuration + settings + info
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎙️ ToneShift")
    st.caption("AI-powered tone & style converter")
    st.divider()

    st.markdown("#### ⚙️ Conversion Settings")
    selected_tone = st.selectbox(
        "Target tone",
        options=SUPPORTED_TONES,
        index=0,
        help="Choose the tone the rewritten text should adopt.",
    )
    creativity = st.slider(
        "Creativity (temperature)",
        min_value=0.0,
        max_value=1.0,
        value=float(settings.default_temperature),
        step=0.05,
        help="Lower = more literal & predictable. Higher = more creative & varied.",
    )
    response_length = st.select_slider(
        "Response length",
        options=list(RESPONSE_LENGTH_MAP.keys()),
        value="Medium",
        help="Roughly how long the converted text should be relative to the input.",
    )

    st.divider()
    st.markdown("#### 🔌 Provider")

    model_name = {
        "openai": settings.openai_model,
        "groq": settings.groq_model,
        "openrouter": settings.openrouter_model,
    }.get(settings.llm_provider, "Unknown")

    st.markdown(
        f"<span class='stat-pill'>Provider: {settings.llm_provider}</span>"
        f"<span class='stat-pill'>Model: {model_name}</span>",
        unsafe_allow_html=True,
    )

    st.caption(
        "Switch providers by changing `LLM_PROVIDER` in your `.env` file "
        "(openai / groq / openrouter). No code changes required."
    )

    st.divider()
    if st.session_state.history:
        if st.button("🗑️ Clear history", use_container_width=True):
            st.session_state.history = []
            st.rerun()

    st.divider()
    st.caption("Built for the AI Engineering Launchpad · Streamlit + LLM")


# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
st.markdown("<div class='toneshift-header'>🎙️ ToneShift</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='toneshift-subheader'>Rewrite any text in the tone you need — "
    "formal, friendly, persuasive, and more — powered by a large language model.</div>",
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------
# Main input area
# --------------------------------------------------------------------------
left_col, right_col = st.columns([1, 1], gap="large")

with left_col:
    st.markdown("#### 📝 Original Text")
    input_text = st.text_area(
        label="Enter the text you want to convert",
        value=st.session_state.input_text,
        height=280,
        max_chars=settings.max_input_characters,
        placeholder=(
            "Paste or type the text you want to rewrite... e.g.\n\n"
            "\"Hey team, the deadline moved up, we need this done by Friday, "
            "no excuses.\""
        ),
        key="input_text_area",
    )

    button_col1, button_col2 = st.columns([1, 1])
    with button_col1:
        convert_clicked = st.button(
            "✨ Convert", type="primary", use_container_width=True
        )
    with button_col2:
        regenerate_clicked = st.button(
            "🔁 Regenerate",
            use_container_width=True,
            disabled=st.session_state.last_result is None,
            help="Re-run the last conversion (useful with creativity > 0).",
        )

with right_col:
    st.markdown("#### ✅ Converted Text")
    output_placeholder = st.empty()
    meta_placeholder = st.empty()

    if st.session_state.last_result is None:
        output_placeholder.info(
            "Your converted text will appear here after you click **Convert**."
        )


# --------------------------------------------------------------------------
# Core conversion routine
# --------------------------------------------------------------------------
def run_conversion(raw_text: str, tone: str, temperature: float, length: str) -> None:
    """Validates input, calls the LLM, updates session state, and renders output."""
    try:
        clean_text = validate_input_text(raw_text, settings.max_input_characters)
        clean_temperature = validate_temperature(temperature)
    except ValidationError as exc:
        st.error(f"⚠️ {exc}")
        return

    system_prompt = build_system_prompt(tone)
    user_prompt = build_user_prompt(clean_text, length)

    try:
        with st.spinner(f"Converting to **{tone}** tone..."):
            client = build_llm_client(settings)
            start_time = time.perf_counter()
            response = client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=clean_temperature,
            )
            elapsed_seconds = round(time.perf_counter() - start_time, 2)
    except LLMClientError as exc:
        st.error(f"❌ Conversion failed: {exc}")
        return
    except Exception as exc:  # noqa: BLE001 - final safety net for the UI
        st.error(f"❌ An unexpected error occurred: {exc}")
        return

    original_stats = compute_text_stats(clean_text)
    converted_stats = compute_text_stats(response.text)

    result = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tone": tone,
        "temperature": clean_temperature,
        "length": length,
        "original_text": clean_text,
        "converted_text": response.text,
        "provider": response.provider,
        "model": response.model,
        "elapsed_seconds": elapsed_seconds,
        "total_tokens": response.total_tokens,
        "original_stats": original_stats,
        "converted_stats": converted_stats,
    }

    st.session_state.last_result = result
    st.session_state.history.insert(0, result)
    st.session_state.history = st.session_state.history[:20]  # cap history size
    st.success("✅ Conversion complete!")


# --------------------------------------------------------------------------
# Handle button clicks
# --------------------------------------------------------------------------
if convert_clicked:
    run_conversion(input_text, selected_tone, creativity, response_length)

if regenerate_clicked and st.session_state.last_result is not None:
    prev = st.session_state.last_result
    run_conversion(
        prev["original_text"], prev["tone"], prev["temperature"], prev["length"]
    )


# --------------------------------------------------------------------------
# Render the latest result (persists across reruns/regenerations)
# --------------------------------------------------------------------------
result = st.session_state.last_result
if result is not None:
    with right_col:
        output_placeholder.markdown(
            f"<div class='toneshift-card'>{result['converted_text']}</div>",
            unsafe_allow_html=True,
        )

        o_stats = result["original_stats"]
        c_stats = result["converted_stats"]
        word_delta = percentage_change(o_stats.word_count, c_stats.word_count)

        meta_placeholder.markdown(
            f"<span class='stat-pill'>Words: {c_stats.word_count} "
            f"({'+' if word_delta >= 0 else ''}{word_delta}% vs original)</span>"
            f"<span class='stat-pill'>Characters: {c_stats.character_count}</span>"
            f"<span class='stat-pill'>Tone: {result['tone']}</span>"
            f"<span class='stat-pill'>Model: {result['model']}</span>"
            f"<span class='stat-pill'>Latency: {result['elapsed_seconds']}s</span>",
            unsafe_allow_html=True,
        )

        st.text_area(
            "Copy-friendly output (select all → copy)",
            value=result["converted_text"],
            height=120,
            key="copy_output_area",
        )

        dl_col, _ = st.columns([1, 2])
        with dl_col:
            st.download_button(
                label="⬇️ Download as .txt",
                data=result["converted_text"],
                file_name=f"toneshift_{result['tone'].lower().replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True,
            )

    st.divider()
    with st.expander("🔍 Show original text & comparison stats"):
        comp_col1, comp_col2 = st.columns(2)
        with comp_col1:
            st.markdown("**Original**")
            st.write(result["original_text"])
            st.caption(
                f"{o_stats.word_count} words · {o_stats.character_count} characters"
            )
        with comp_col2:
            st.markdown("**Converted**")
            st.write(result["converted_text"])
            st.caption(
                f"{c_stats.word_count} words · {c_stats.character_count} characters"
            )

    with st.expander("🧠 Show exact prompts sent to the LLM (for viva demonstration)"):
        st.markdown("**System Prompt**")
        st.code(build_system_prompt(result["tone"]), language="text")
        st.markdown("**User Prompt**")
        st.code(
            build_user_prompt(result["original_text"], result["length"]),
            language="text",
        )
        st.caption(
            f"Provider: {result['provider']} · Model: {result['model']} · "
            f"Total tokens: {result['total_tokens']}"
        )


# --------------------------------------------------------------------------
# History panel
# --------------------------------------------------------------------------
if st.session_state.history:
    st.divider()
    st.markdown("#### 🕘 Recent Conversions")
    for item in st.session_state.history[:8]:
        preview = item["converted_text"][:140]
        ellipsis = "..." if len(item["converted_text"]) > 140 else ""
        st.markdown(
            f"<div class='history-item'>"
            f"<b>{item['tone']}</b> · {item['timestamp']}<br>"
            f"{preview}{ellipsis}"
            f"</div>",
            unsafe_allow_html=True,
        )
