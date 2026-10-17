# Configurable LLM providers

## Summary

- Replaced separate Mistral client setup with one shared `get_llm()` factory for generation and RAG chat.
- Added support for Mistral, Gemini, Groq, OpenAI, Anthropic, and custom OpenAI-compatible endpoints.
- Select the provider, model, and matching API key in `.env`, then restart the app; no dropdown is needed.
- The factory loads only the chosen integration and reports missing settings or packages instead of silently switching providers.
- Added dependencies, configuration examples, and validation checks while preserving existing Mistral settings.

## Details

Update: 2026-10-17. Implementation commit: `e3a27bb` (`add configurable LLM providers`).

### What changed

Title generation, summarization, extraction, and conversational RAG now use
`get_llm()` from `core/llm.py`. Previously, each module created its own
hard-coded Mistral client. Provider and model selection now come from `.env`;
there is no provider dropdown in the app.

### Configuration

Set `LLM_PROVIDER`, `LLM_MODEL`, and the selected provider's API key:

- `mistral`: `MISTRAL_API_KEY`
- `gemini`: `GOOGLE_API_KEY`
- `groq`: `GROQ_API_KEY`
- `openai`: `OPENAI_API_KEY`
- `anthropic`: `ANTHROPIC_API_KEY`
- `openai_compatible`: `LLM_API_KEY` and `LLM_BASE_URL`

For example, to use Claude:

```env
LLM_PROVIDER=anthropic
LLM_MODEL=your_available_claude_model_id
ANTHROPIC_API_KEY=your_actual_key
```

Choose a model ID available to your account. Only the selected provider's key
is required. For a custom OpenAI-compatible endpoint, set `LLM_BASE_URL` to
the service's API base URL, usually ending in `/v1`.

Restart the app after changing `.env`. Existing shell environment variables
take precedence over `.env`, so remove stale shell values if needed.
`.env.example` lists all supported settings; real keys remain in the ignored
local `.env` file.

### Implementation and behavior

- `core/analysis.py` and `core/rag_engine.py` use the shared factory. The summarizer and extractor compatibility helpers reuse the shared analysis implementation.
- `Requirements.txt` includes the Mistral, Gemini, Groq, OpenAI, and Anthropic integrations. Install the updated requirements when setting up another environment.
- Only the selected provider's integration is imported at runtime.
- Unknown providers, missing or placeholder keys, missing model configuration, and missing integrations produce configuration errors. The factory does not silently switch providers.
- Existing configurations containing only `MISTRAL_API_KEY` continue to use `mistral-small-latest`.
- Shared meeting analysis uses temperature `0.2`; RAG uses `0.3`. Select a model that supports these settings.
- Gemini uses the Developer API rather than Vertex AI.
- Transcription and local embeddings use their own configuration. See [Shared chunk analysis](shared-chunk-analysis.md) for the generation and merging flow.

### Verification

Local validation covered provider routing, model/key selection, legacy Mistral
settings, and configuration failures. All six provider
clients initialized with dummy credentials without sending API requests.
Dependency checks found no broken requirements, and Git whitespace checks passed.
Live generation was not tested; it requires a valid key, model access, and quota.
