# Multi-Turn Conversational RAG

## Summary

- Added conversational context so the chatbot can understand follow-ups such as "Who approved it?"
- Keep the latest four messages and summarize older turns into at most four lines before rewriting the question.
- The LLM turns the follow-up into a standalone question, then Chroma retrieves relevant transcript chunks.
- The answer LLM receives the rewritten question and retrieved context, keeping full chat history out of the final answer request.
- Both the app and CLI pass conversation history; clearing the app chat resets the context used for future follow-ups.

## Details

### What Changed

The chatbot now supports follow-up questions such as `Who approved it?` after an earlier question about a decision.

Previously, every question was retrieved and answered independently. Now, previous conversation turns are used to rewrite follow-up questions into standalone retrieval questions.

### New Request Flow

```text
Current question + compact conversation history
                |
                v
       Rewrite into standalone question
                |
                v
       Retrieve transcript context
                |
                v
       Generate answer from revised question + context
```

### Implementation Details

#### 1. History preparation

`ConversationalRAGChain` in `core/rag_engine.py`:

- Converts application dictionaries into LangChain message objects.
- Keeps the latest 4 messages unchanged.
- Summarizes older messages in a maximum of 4 lines.
- Uses the compacted history only for question rewriting.

Here, one message means one entry from either the user or the assistant. Therefore, the latest 4 messages normally represent 2 complete user/assistant exchanges:

```text
1. User question
2. Assistant answer
3. User follow-up
4. Assistant answer
```

The four messages are selected in chronological order from the end of the conversation. Any messages before them are included only in the older-history summary.

#### 2. Question rewriting

The rewrite prompt receives:

- The compacted previous conversation.
- The current user question.

It produces a standalone question by resolving references such as `it`, `they`, or `that decision`.

Example:

```text
Previous: The launch was moved to Friday.
Current: Who approved it?
Revised: Who approved moving the launch to Friday?
```

#### 3. Retrieval

The revised question is sent to the existing Chroma vector-store retriever. The retriever returns the most relevant transcript chunks.

#### 4. Final answer

The final-answer prompt receives only:

- The revised standalone question.
- Retrieved transcript context.

The final prompt does not receive the full chat history. This keeps the answer request smaller and instructs the model to ground its answer in retrieved transcript context.

If the retrieved context does not contain the answer, the prompt instructs the model to use this fallback response:

```text
I could not find this information in the meeting transcript.
```

### API Changes

`ask_question` now accepts optional history:

```python
answer = ask_question(rag_chain, question, chat_history)
```

Plain string invocation remains supported for one-off questions.

### Application Integration

- `app.py` passes `st.session_state.chat_history` before adding the current turn.
- `main.py` maintains and updates `chat_history` during CLI sessions.
- Clearing the Streamlit chat removes the history used for future rewrites.

### Token Protection

History is bounded before it reaches the rewrite prompt:

- Recent history: 4 individual messages, normally 2 complete user/assistant exchanges.
- Older history: maximum 4 summary lines.
- Final-answer prompt: revised question and transcript context only.

A conversation with older messages therefore does not send the complete chat history to the final-answer LLM.

### Changed Files

- `core/rag_engine.py`: conversational chain, history compaction, rewriting, and revised final-answer flow.
- `app.py`: passes Streamlit chat history.
- `main.py`: maintains CLI chat history.

### Validation

- `python -m py_compile core/rag_engine.py` passed.
- Static diagnostics passed.
- `git diff --check` passed.
