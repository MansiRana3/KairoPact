# Engineering Principles & Architecture
### The goal:
> Build systems that are easy to understand, easy to debug, and easy to extend — without over-engineering.

# CORE PRINCIPLES
## 1. Readability > Cleverness
- Code should be understandable in **one pass**
- Avoid unnecessary abstractions
- Prefer explicit logic over “smart” patterns

Bad:
- Splitting 5 lines into 3 functions used once
- Deep nesting of abstractions

Good:
- Straightforward, linear, readable flow


This is a FastAPI + LLM service. All business logic flows through one path:
`router.py` → `service.py` → `agents.py` → `service.py`

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for layer rules and folder structure.
See [docs/CONVENTIONS.md](docs/CONVENTIONS.md) for coding rules and anti-patterns.
See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for adding features and environment setup.

---

## Verification — run before every commit

```bash
uv run pytest -x           # stop on first failure
uv run ruff check app/     # zero errors required
uv run mypy app/           # zero errors required
```

If any command fails, fix it before committing. Do not skip.

---

## Core rules

- `service.py` owns all logic and flow. Nothing else decides order or branching.
- All LLM calls are `async`. Never use `def` for I/O-bound work.
- All agents use `@retry` (tenacity) and return Pydantic models — never raw strings.
- All prompts live in `core/prompts_and_instructions/` — never inlined in code.
- Never hardcode secrets. Use `.env` via `app/core/config.py`.