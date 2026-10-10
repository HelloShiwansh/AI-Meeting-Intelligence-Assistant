"""Build downloadable meeting results in memory, without model or API calls."""

import json
import re
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile


RESULT_SECTIONS = (
    ("summary", "Summary"),
    ("action_items", "Action Items"),
    ("key_decisions", "Key Decisions"),
    ("open_questions", "Open Questions"),
    ("transcript", "Full Transcript"),
)


def export_filename(title: str) -> str:
    """Return a bounded filename safe for Windows and ZIP entries."""
    stem = re.sub(r"[^\w-]+", "_", title, flags=re.UNICODE).strip("_-")[:80]
    # A prefix also avoids reserved Windows filenames such as CON and NUL.
    return f"meeting_{stem}" if stem else "meeting_results"


def format_chat(chat_history: list[dict]) -> str:
    return "\n\n".join(
        f"{'You' if message['role'] == 'user' else 'Assistant'}:\n{message['content']}"
        for message in chat_history
    )


def build_downloads(result: dict, chat_history: list[dict]) -> dict[str, bytes]:
    """Whitelist export fields; the live RAG chain is never serialized."""
    title = result["title"]
    sections = [(label, result[key]) for key, label in RESULT_SECTIONS]
    if chat_history:
        sections.append(("Meeting Chat", format_chat(chat_history)))

    markdown = f"# {title}\n\n" + "\n\n".join(
        f"## {label}\n\n{content}" for label, content in sections
    ) + "\n"
    plain_text = f"{title}\n\n" + "\n\n".join(
        f"{label}\n{'=' * len(label)}\n{content}" for label, content in sections
    ) + "\n"
    structured = {"title": title, **{key: result[key] for key, _ in RESULT_SECTIONS}}
    structured["chat_history"] = [
        {"role": message["role"], "content": message["content"]}
        for message in chat_history
    ]

    files = {
        "report.md": markdown.encode("utf-8"),
        "report.txt": plain_text.encode("utf-8"),
        "results.json": json.dumps(structured, ensure_ascii=False, indent=2).encode("utf-8"),
        **{f"{key}.txt": result[key].encode("utf-8") for key, _ in RESULT_SECTIONS},
    }
    if chat_history:
        files["chat.txt"] = format_chat(chat_history).encode("utf-8")

    archive = BytesIO()
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
        for filename, content in files.items():
            bundle.writestr(filename, content)
    files["all_results.zip"] = archive.getvalue()
    return files
