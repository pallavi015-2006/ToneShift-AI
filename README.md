# 🎙️ ToneShift – AI Tone Converter

An AI-powered writing assistant that rewrites any text in a chosen tone —
Formal, Friendly, Professional, Persuasive, Academic, and more — built with
**Streamlit** for the UI and a **provider-agnostic LLM layer** (OpenAI /
Groq / OpenRouter) for the generation backend.

Built for a university **AI Engineering Launchpad** submission: clean
layered architecture, full error handling, unit tests, and demonstration
guidance for a faculty viva.

---

## 1. Project Structure

```
toneshift/
├── app.py                     # Streamlit UI entry point (orchestration only)
├── config.py                  # Environment loading, constants, Settings dataclass
├── requirements.txt           # Pinned Python dependencies
├── .env.example                # Reference environment file (copy to .env)
├── .streamlit/
│   └── config.toml            # Dark-mode-friendly theme configuration
├── llm/
│   ├── __init__.py
│   ├── base.py                 # Abstract LLMClient interface + typed exceptions
│   ├── openai_client.py        # Concrete OpenAI-compatible client (OpenAI/Groq/OpenRouter)
│   └── factory.py               # Picks the right client based on LLM_PROVIDER
├── prompts/
│   ├── __init__.py
│   └── templates.py             # All prompt-engineering logic (system + user prompts)
├── utils/
│   ├── __init__.py
│   ├── validators.py             # Input validation (empty text, length, temperature)
│   └── text_utils.py             # Word/character counting, % change helper
└── tests/
    ├── __init__.py
    ├── test_utils.py              # Unit tests for validators + text stats
    └── test_prompts.py            # Unit tests for prompt construction
```

### Why this structure? (viva talking point)

This follows a **clean/layered architecture** with strict separation of
concerns, so each layer can be explained, tested, and swapped independently:

| Layer          | Responsibility                                   | Depends on          |
|----------------|---------------------------------------------------|---------------------|
| `app.py`       | UI rendering, session state, user interaction      | everything below    |
| `prompts/`     | Prompt engineering (what we ask the model)         | `config`            |
| `llm/`         | How we talk to a model provider (transport, retries, error normalization) | `config` |
| `utils/`       | Pure, stateless helper functions                    | nothing             |
| `config.py`    | Environment & constants, single source of truth     | `python-dotenv`     |

Because `llm/base.py` defines an abstract `LLMClient` interface, **swapping
providers is a one-line `.env` change** (`LLM_PROVIDER=groq`) — no code in
`app.py` or `prompts/` ever needs to change. This is the single most
important architectural decision to highlight during evaluation.

---

## 2. Installation & Setup

### Prerequisites
- Python 3.10+
- An API key from OpenAI (default), or Groq / OpenRouter if you plan to
  switch providers.

### Steps

```bash
# 1. Clone / unzip the project, then move into it
cd toneshift

# 2. (Recommended) create a virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# then open .env and paste your real API key, e.g.:
#   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# 5. Run the app
streamlit run app.py
```

The app opens automatically at **http://localhost:8501**.

### Running tests

```bash
pytest tests/ -v
```

All 23 unit tests should pass without requiring an API key (they test
pure logic only — validation and prompt construction — never call the
network).

---

## 3. Switching LLM Providers

`llm/openai_client.py` implements the OpenAI **Chat Completions** schema,
which OpenAI, Groq, and OpenRouter all support natively. Switching is a
config-only change:

```dotenv
# .env

# Use OpenAI (default)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# OR use Groq (fast, often free-tier friendly)
LLM_PROVIDER=groq
GROQ_API_KEY=gsk-...
GROQ_MODEL=llama-3.3-70b-versatile

# OR use OpenRouter (access many models through one key)
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=openai/gpt-4o
```

No file other than `.env` needs to change. `llm/factory.py` reads
`LLM_PROVIDER` and instantiates the corresponding client.

---

## 4. Data Flow (End-to-End)

```
 ┌─────────────┐   1. text + tone + sliders   ┌────────────┐
 │  Streamlit  │ ───────────────────────────▶ │   app.py   │
 │     UI      │                               │(run_conversion)
 └─────────────┘                               └─────┬──────┘
                                                       │ 2. validate
                                                       ▼
                                          ┌────────────────────────┐
                                          │ utils/validators.py     │
                                          │ (empty / too-long check)│
                                          └───────────┬─────────────┘
                                                       │ 3. build prompts
                                                       ▼
                                          ┌────────────────────────┐
                                          │ prompts/templates.py    │
                                          │ (system + user prompt)  │
                                          └───────────┬─────────────┘
                                                       │ 4. get client
                                                       ▼
                                          ┌────────────────────────┐
                                          │ llm/factory.py           │
                                          │ → llm/openai_client.py   │
                                          └───────────┬─────────────┘
                                                       │ 5. HTTPS request
                                                       ▼
                                          ┌────────────────────────┐
                                          │  Provider API            │
                                          │ (OpenAI / Groq / OpenRouter)│
                                          └───────────┬─────────────┘
                                                       │ 6. normalized LLMResponse
                                                       ▼
                                          ┌────────────────────────┐
                                          │ utils/text_utils.py      │
                                          │ (word/char stats)        │
                                          └───────────┬─────────────┘
                                                       │ 7. render
                                                       ▼
                                                 Streamlit UI
                                        (converted text, stats, history)
```

1. The user types text into the left panel and picks a **tone**,
   **creativity** (temperature), and **response length** in the sidebar.
2. On clicking **Convert**, `app.py` validates the input (non-empty,
   under the character limit).
3. `prompts/templates.py` builds a **system prompt** (tone rules + strict
   output-format rules) and a **user prompt** (length guidance + the
   text itself).
4. `llm/factory.py` builds the client configured by `LLM_PROVIDER`.
5. `llm/openai_client.py` calls the provider's Chat Completions endpoint,
   with automatic retries (via `tenacity`) on transient network/rate-limit
   errors, and normalizes provider-specific exceptions into typed errors
   (`AuthenticationError`, `RateLimitError`, `NetworkError`,
   `InvalidRequestError`).
6. The normalized `LLMResponse` (text + token usage + latency) flows back.
7. `app.py` computes word/character statistics, stores the result in
   `st.session_state` (for history and regeneration), and renders it.

---

## 5. Features

### Core (MVP)
- ✅ Large text input with live character limit enforcement
- ✅ 12 tone presets: Formal, Friendly, Professional, Casual, Academic,
  Persuasive, Funny, Motivational, Child Friendly, Email, Social Media,
  Customer Support
- ✅ Creativity slider (temperature 0.0–1.0)
- ✅ Response length control (Short / Medium / Long)
- ✅ Convert button with spinner + success/error states
- ✅ Output panel: converted text, word/character counts, % change vs
  original
- ✅ Robust error handling: empty input, oversized input, invalid API
  key, rate limits, network/timeout failures, malformed provider
  responses

### Bonus features included
- ✅ **History panel** — last 20 conversions kept in session, 8 shown
- ✅ **Download as .txt** button
- ✅ **Regenerate** button (re-runs the last conversion, useful to see
  variation when creativity > 0)
- ✅ **Copy-friendly text area** for the converted output
- ✅ **Dark-mode-friendly theme** (`.streamlit/config.toml`)
- ✅ **Prompt transparency panel** — expandable section showing the
  *exact* system/user prompts sent to the model (ideal for a viva)
- ✅ **Unit tests** for validation, text statistics, and prompt building

---

## 6. Error Handling Reference

| Scenario                                  | Where it's caught              | User sees                                  |
|--------------------------------------------|----------------------------------|---------------------------------------------|
| Empty / whitespace-only input               | `utils/validators.py`            | "Please enter some text to convert."         |
| Input exceeds character limit               | `utils/validators.py`            | "Input is too long (...)"                    |
| Missing/invalid API key                     | `llm/openai_client.py`           | "Authentication failed for provider ..."     |
| Provider rate limit hit                     | `llm/openai_client.py` (+ retry) | "Rate limit reached ..." (auto-retried first)|
| Network timeout / connection failure        | `llm/openai_client.py` (+ retry) | "Could not reach ..." (auto-retried first)   |
| Malformed request / bad model name          | `llm/openai_client.py`           | "The request was rejected by ..."            |
| Empty response from provider                | `llm/openai_client.py`           | "Provider returned an empty response."       |
| Any other unexpected exception              | `app.py` safety net              | "An unexpected error occurred: ..."          |

---

## 7. Demonstration Guide for Faculty Evaluation (Viva)

A suggested 10–12 minute walkthrough:

1. **Architecture overview (2 min)** — Open the project tree and explain
   the four layers (`app.py`, `prompts/`, `llm/`, `utils/`) using the
   table in Section 1. Emphasize the **abstraction boundary**: `app.py`
   never imports `openai` directly, only `llm.factory`.

2. **Live conversion demo (3 min)** —
   - Paste a plain sentence, e.g. *"Hey team, the deadline moved up, we
     need this done by Friday, no excuses."*
   - Convert to **Professional**, then **Funny**, then **Child Friendly**,
     showing how tone changes while meaning is preserved.
   - Point out the word/character stats and latency shown after each run.

3. **Prompt transparency (2 min)** — Expand "Show exact prompts sent to
   the LLM" to show the grader precisely what was engineered — this
   directly demonstrates prompt-engineering skill, not just API plumbing.

4. **Error handling demo (2 min)** —
   - Click Convert with an empty text box → show the validation message.
   - Temporarily rename `OPENAI_API_KEY` in `.env` to an invalid value,
     restart the app, and show the clean "Authentication failed" message
     instead of a raw stack trace.

5. **Provider-swap demo (1 min, optional)** — Show the `.env` file and
   explain that changing `LLM_PROVIDER=openai` to `LLM_PROVIDER=groq`
   (with a Groq key set) is the only change needed to run on a different
   backend — no code edits.

6. **Testing (1 min)** — Run `pytest tests/ -v` live to show all 23 tests
   passing, covering validation and prompt-construction logic.

7. **Bonus features (1 min)** — Show history, regenerate, and the
   download-as-.txt button.

### Suggested evaluation criteria mapping

| Criterion                          | Where it's demonstrated                                   |
|--------------------------------------|--------------------------------------------------------------|
| Software architecture / modularity   | Layered project structure, `LLMClient` abstraction            |
| Prompt engineering                    | `prompts/templates.py`, the transparency expander              |
| Robustness / error handling           | Section 6 table, live error demo                                |
| Testing discipline                    | `tests/`, live `pytest` run                                     |
| UI/UX quality                          | Streamlit layout, dark theme, cards, stat pills, history panel  |
| Extensibility                         | Multi-provider support via one factory function                 |

---

## 8. Configuration Reference (`.env`)

See `.env.example` for the full annotated reference. Key variables:

| Variable                     | Purpose                                             | Default                  |
|-------------------------------|-------------------------------------------------------|---------------------------|
| `LLM_PROVIDER`                | `openai` \| `groq` \| `openrouter`                    | `openai`                 |
| `OPENAI_API_KEY`              | Your OpenAI secret key                                | *(required for openai)*  |
| `OPENAI_MODEL`                | Model name                                             | `gpt-4o`                 |
| `REQUEST_TIMEOUT_SECONDS`     | Per-request timeout                                    | `30`                      |
| `MAX_INPUT_CHARACTERS`        | Max characters allowed in the input box                | `6000`                    |
| `DEFAULT_TEMPERATURE`         | Default creativity slider position                     | `0.7`                     |

---

## 9. Known Limitations & Future Work

- No persistent storage — history resets when the Streamlit session ends
  (an easy extension: swap `st.session_state.history` for a SQLite/JSON
  file).
- No user authentication — acceptable for a single-user academic demo,
  but would be needed for multi-user deployment.
- No streaming token-by-token output — could be added by switching to
  the provider's streaming API and `st.write_stream`.
- No automated evaluation of *tone accuracy* (e.g. an LLM-as-judge check)
  — a natural "Phase 2" extension for a more advanced course project.

---

## 10. License

This project was created for academic coursework purposes as part of an
AI Engineering Launchpad submission.
