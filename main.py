from dotenv import load_dotenv

load_dotenv()

from utils.audio_processor import process_input
from core.transcriber import transcribe_all
from core.analysis import analyze_meeting
from core.rag_engine import build_rag_chain, ask_question


def run_pipeline(source :str, language :str = "english") -> dict:
    print("starting AI Video Assistant")

    chunks = process_input(source)

    transcript = transcribe_all(chunks,language)
    print(f"raw transcription (first 300 characters ) {transcript[:300]}")

    analysis = analyze_meeting(transcript)
    
    rag_chain = build_rag_chain(transcript)

    return {
        **analysis,
        "transcript": transcript,
        "rag_chain": rag_chain,
    }

if __name__ == "__main__":
    # CLI entry point
    source = input("Enter YouTube / Loom URL or local file path: ").strip()
    language = input("Language (english/hinglish): ").strip() or "english"
    result = run_pipeline(source, language)

    print("\n" + "=" * 60)
    print(f"📌 Title: {result['title']}")
    print(f"\n📋 Summary:\n{result['summary']}")
    print(f"\n✅ Action Items:\n{result['action_items']}")
    print(f"\n🔑 Key Decisions:\n{result['key_decisions']}")
    print(f"\n❓ Open Questions:\n{result['open_questions']}")
    print("=" * 60)

    # Phase 2 — Chat with your meeting via RAG
    print("\n💬 Chat with your meeting (type 'exit' to quit)\n")
    rag_chain = result["rag_chain"]
    chat_history = []
    while True:
        question = input("You: ").strip()
        if question.lower() in ["exit", "quit", "q"]:
            print("👋 Goodbye!")
            break
        if not question:
            continue
        answer = ask_question(rag_chain, question, chat_history)
        chat_history.extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ])
        print(f"\n🤖 Assistant: {answer}\n")
