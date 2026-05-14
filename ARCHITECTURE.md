# Architecture

## The flow

```
router.py  →  service.py  →  agents.py
  (HTTP)      (logic)         (LLM task)
```

A developer should be able to understand the full request lifecycle without opening more than 3 files. If you find yourself needing more, the logic is in the wrong place.

---

## Folder structure

```
app/
├── core/
│   ├── config.py                  # env vars loaded from .env
│   ├── logger.py                  # centralised logging
│   ├── security.py                # API key verification
│   └── prompts_and_instructions/  # all LLM prompt text lives here
└── v1/
    ├── router.py                  # HTTP endpoints only
    ├── service.py                 # all business logic and flow control
    ├── agents.py                  # LLM calls with retries
    ├── schemas.py                 # Pydantic models for I/O and LLM outputs
    └── utils.py                   # pure, stateless helper functions

tests/
└── v1/                            # mirrors app/v1/ exactly
    ├── test_service.py
    ├── test_agents.py
    └── test_utils.py
```

---

## Layer responsibilities

| Layer | File | Owns |
|-------|------|------|
| HTTP | `router.py` | Receives request, validates via `schemas.py`, calls `service.py`, returns response. No business logic. |
| Flow | `service.py` | The sole owner of logic. Decides what happens, in what order. Handles business-level errors. |
| Tasks | `agents.py` | Executes isolated LLM tasks. Handles API retries. No routing, no app-state branching. |
| Data | `schemas.py` | Pydantic models for HTTP I/O and LLM structured outputs. |
| Helpers | `utils.py` | Pure, deterministic, synchronous functions only (formatting, parsing, token counting). |
| Prompts | `core/prompts_and_instructions/` | Prompt text only. No Python logic. |

---

## Service layer — the flow owner

`service.py` contains the entire flow from top to bottom. It coordinates agents; agents never coordinate each other.

```python
# app/v1/service.py
async def process_chat_summary(chat_history: list, user_id: str):
    logger.info(f"Starting summary flow for user {user_id}")
    formatted_chat = "\n".join([f"{msg.role}: {msg.content}" for msg in chat_history])

    try:
        # service.py decides the order — not the agents
        intent = await classify_intent(formatted_chat)
        summary = await summarize_chat(formatted_chat)
    except Exception as e:
        logger.error(f"LLM failed for {user_id}: {e}")
        return {"status": "error", "message": "AI service unavailable"}

    return {"status": "success", "intent": intent.label, "data": summary.model_dump()}
```

---

## Agents layer — task execution

Each agent does one thing, handles its own retries, and returns a Pydantic model.

```python
# app/v1/agents.py
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
async def summarize_chat(chat_text: str) -> SummaryOutput:
    prompt = get_summarizer_prompt()
    start = time.time()
    response = await client.beta.chat.completions.parse(
        model="claude-sonnet-4-20250514",
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": chat_text}],
        response_format=SummaryOutput,
    )
    logger.info(f"summarize_chat | {time.time()-start:.2f}s | {response.usage.total_tokens} tokens")
    return response.choices[0].message.parsed
```

---

## Debugging

Because the architecture is linear, so is debugging:

1. HTTP / validation failure → `router.py`, `schemas.py`
2. Business logic failure → `service.py`
3. LLM timeout or API error → `agents.py` (retry logs)
4. LLM returning wrong data → `core/prompts_and_instructions/`

You should never need to open more than 3 files to understand a bug.