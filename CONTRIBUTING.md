# Contributing

## Adding a new capability

Follow this order every time. Do not skip steps.

1. **Schema** → Add input/output Pydantic models to `schemas.py`.
2. **Prompt** → Write the prompt in `core/prompts_and_instructions/`.
3. **Agent** → Add a new `async` function to `agents.py` with `@retry`, returning a Pydantic model.
4. **Service** → Wire the agent call into `service.py`. This is the only place that decides order and logic.
5. **Router** → Add an HTTP endpoint to `router.py` if needed. It calls `service.py` and nothing else.
6. **Tests** → Add tests to `tests/v1/` mirroring the file you changed.

---

## Environment & dependencies

```bash
uv add <package>                      # add a dependency — never use raw pip
uv run uvicorn main:app --reload      # run locally
```

- All environment variables are loaded from `.env` via `app/core/config.py`.
- `.env.example` must document every required variable. Update it whenever you add one.
- Never hardcode secrets, API keys, or environment-specific values in code.

---

## Pre-commit checklist

- [ ] `uv run pytest -x` passes
- [ ] `uv run ruff check app/` passes
- [ ] `uv run mypy app/` passes
- [ ] Full flow is visible top-to-bottom in `service.py`
- [ ] All LLM calls are `async`/`await`
- [ ] All agents use `@retry` and return Pydantic models
- [ ] All prompts are in `core/prompts_and_instructions/`, not inlined
- [ ] New env variables are documented in `.env.example`
- [ ] Tests exist for any new logic in `tests/v1/`
- [ ] No secrets or hardcoded config values in code