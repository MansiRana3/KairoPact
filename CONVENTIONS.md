# Conventions

## LLM & async rules

- **Always async.** LLM calls are I/O bound. Use `async def` / `await` in all agent and service functions. Never block the FastAPI event loop.
- **`utils.py` is synchronous.** Only make a function async if it does I/O. Don't over-asyncify helpers.
- **Always retry.** Use `@retry` (tenacity) in `agents.py` for all LLM calls. Transient 502s, timeouts, and rate limits are normal — don't let them surface as user errors.
- **Always structured outputs.** Agents return Pydantic models, not raw strings. This enforces a strict data contract between the agent and service layers.
- **Always log observability.** Log prompt tokens, completion tokens, and latency on every LLM call. Bugs in AI systems are often cost or latency issues, not stack traces.

---

## Prompts

- All prompt text lives in `core/prompts_and_instructions/`. Never inline a multi-line prompt in `agents.py`.
- Use named placeholders (`{chat_text}`, `{user_name}`) so prompts are testable and readable.
- No Python logic in the prompts folder.

---

## Anti-patterns

| Never do this | Why |
|---|---|
| `def` instead of `async def` for LLM calls | Blocks the entire FastAPI event loop |
| Agents calling other agents | Hides flow control; `service.py` must own all coordination |
| Business logic in `router.py` | Routers are HTTP plumbing only |
| Inline multi-line prompts in `agents.py` | Makes prompts untestable and hard to version |
| Hardcoded secrets or env-specific values | Security risk; breaks across environments |
| Skipping `@retry` on LLM calls | One flaky API response becomes a user-facing error |
| Base classes or inheritance for simple LLM calls | Unnecessary indirection; prefer plain async functions |