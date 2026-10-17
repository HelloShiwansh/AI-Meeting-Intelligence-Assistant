# Shared chunk analysis

## Summary

- Replaced separate generation passes with shared analysis: each chunk normally produces its summary, tasks, decisions, and question/answer notes in one call.
- Process up to three chunks concurrently, then restore transcript order before merging their notes.
- The merge LLM is asked to remove duplicates, reconcile decisions, connect questions to answers in other chunks, and generate the final title.
- Output length follows the selected provider/client's default; large inputs or cut-off outputs use smaller chunks or merge groups without a forced output-token setting.
- If merging still cannot finish, validated notes are preserved with a visible "Review needed" notice; truncated responses are never treated as complete results.

## Details

Update: 2026-10-17.

### Behavior

`core/analysis.py` normally analyzes each overlapping transcript section in one
LLM call. Recovery can add calls when a response is incomplete or a request is
too large. Each valid response contains the title candidate, summary, action items with
owners/deadlines, decisions, and questions with explicit answers. The app, CLI,
and manual `test.py` runner call `analyze_meeting()` once and share its report.
The three full-transcript extraction calls and separate summary/title passes
have been replaced.

Up to three chunk calls run concurrently by default. Results are restored to
transcript order before merging. Progress callbacks run on the calling thread,
so Streamlit state and progress updates are not accessed from worker threads.

### Merge

The normal path uses N chunk calls plus one LLM merge call. The merge prompt
asks the model to deduplicate overlap, preserve distinct commitments and their
owners/deadlines, reconcile changed decisions, and resolve questions using
explicit evidence from any section. Intermediate notes retain answered
questions and their answers for subsequent merges. Final rendering shows only
unanswered questions. The title is generated from the combined material.

When combined notes exceed the request budget, adjacent notes are merged in
batches over multiple levels. Singletons carry forward without another call.
Every request includes prompt/schema overhead in its budget check. If notes
cannot fit even as individual records, merges cannot reduce record count, or
the normal 12-level merge limit is reached, the validated notes are assembled
locally with a review notice rather than discarded.

### Automatic recovery

1. Keep the raw model response metadata. A finish/stop reason of `length`,
   `max_tokens`, or `MAX_TOKENS` indicates a cut-off response, even when the
   returned text happens to be valid JSON. Incomplete JSON is also rejected
   when a custom provider omits this metadata.
2. Leave output length to the provider/client default. No application output
   allowance is sent, and the same input is not repeated just to increase
   output space. No broken response is appended to another response or
   repaired into an apparently complete one.
3. If source extraction hits the output limit, split that source into
   smaller Unicode-safe pieces at a nearby word boundary and retry. Requests
   above the local input budget split before being sent. Recognized provider
   context-size errors also trigger size recovery. Source
   recovery has at most four split levels; every source character is retained.
4. If merging fails, try smaller chronological groups
   with at most three recovery subdivision levels. This is separate from the
   normal batching used for long meetings.
5. If a merge cannot finish, combine only previously validated notes in Python.
   Preserve distinct summaries, tasks with owners/deadlines, decisions, and
   question/answer evidence. Remove exact duplicates only. Explicit conflicting
   answers remain in the summary and their question stays open. This fallback
   uses an existing title candidate and does not claim full semantic matching
   or decision reconciliation.

Fallback reports start their summary with **Review needed**, which is visible
in the app and included in report downloads. The ordinary successful merge
still performs the semantic reconciliation. If source chunks never produce
complete valid notes after bounded recovery, analysis fails explicitly; it
cannot construct a reliable report without extracting the source first.
Authentication, network, and quota errors still propagate. Recovery can add
latency and cost, but recovery recursion is bounded.

### Configuration

The shared provider factory still selects the LLM through `.env`. Optional
analysis settings are documented in `.env.example` and README:

```env
ANALYSIS_MAX_CONCURRENCY=3
ANALYSIS_CHUNK_BUDGET=6000
ANALYSIS_OVERLAP_BUDGET=300
ANALYSIS_INPUT_BUDGET=16000
```

Input budgets use one unit per UTF-8 byte as a conservative offline token
estimate, not native provider counts. No tokenizer download is required.
Output uses the selected provider/client's defaults; no output-size setting
is required. Those defaults are still subject to finite provider and model
limits. Choose input budgets that leave room for the response within the
model's context window. Reduce concurrency to `1` for restrictive free tiers.

### Compatibility and failure handling

The report retains the existing string fields consumed by the UI and exports:
`title`, `summary`, `action_items`, `key_decisions`, and `open_questions`.
The original transcript still goes to RAG indexing. Old generator helpers
remain available; pass the same `analysis=` report to reuse results. Calling
those helpers individually without a shared report starts fresh analysis.

Responses must be complete JSON matching a Pydantic schema. Missing fields,
invalid types, and truncated JSON are rejected. Cut-off extraction can be
retried on smaller source pieces; other invalid extraction fails clearly. Invalid extraction
never becomes a saved partial report; failed model merges use only validated
notes for the clearly marked fallback. This validates response structure, not
semantic accuracy. Reconciliation and completeness remain dependent on the model.
The app publishes results only after analysis and RAG setup both succeed, and
retains the result in session state across ordinary reruns.

Verification: 34 local tests passed, covering request counts, concurrent ordering
and callback thread, bounded recursive merging, malformed responses,
non-progressing merges, Unicode splitting, provider defaults, environment
configuration, compatibility helpers, CLI integration, exports, and provider
configuration. Recovery tests verify that no output allowance is overridden,
length-limit metadata with valid JSON, incomplete JSON without metadata,
smaller source pieces and merge groups, native provider context limits,
ignored legacy output settings, preservation
of distinct tasks and conflicting answers, and propagation of provider errors.
Streamlit tests verify that the app uses shared analysis once, retains it on
reruns, does not publish partial extraction after failures, and displays and
exports the fallback review notice.
Python compilation, dependency checks, and Git whitespace checks also passed.
These checks used a local test suite, which is not included in the repository.
Live API generation requires valid credentials and was not exercised.
