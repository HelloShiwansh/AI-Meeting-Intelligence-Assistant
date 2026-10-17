import json
from uuid import uuid4
from core.transcript import TimestampedTranscript

from langchain_chroma import Chroma 
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

CHROMA_DIR = "vector_db"
COLLECTION_NAME = "meeting_transcript"
EMBEDDING_MODEL  = "all-MiniLM-L6-v2"

def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name = EMBEDDING_MODEL,
        model_kwargs = {"device" : 'cpu'}
    )

def build_documents(transcript, *, video_id: str, source_url: str = "") -> list[Document]:
    """Map character chunks back to the speech segments they overlap."""
    text = transcript.text if isinstance(transcript, TimestampedTranscript) else transcript
    if not text.strip():
        raise ValueError("Cannot index an empty transcript.")
    spans = []
    if isinstance(transcript, TimestampedTranscript):
        position = 0
        for index, segment in enumerate(transcript.segments):
            length = len(segment.text.strip())
            spans.append((position, position + length, index, segment))
            position += length + 1
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50, add_start_index=True)
    docs = splitter.create_documents([text])
    for index, doc in enumerate(docs):
        doc.metadata.update(chunk_index=index, video_id=video_id, source_url=source_url)
        if spans:
            start = doc.metadata["start_index"]
            if start < 0:
                raise ValueError("Could not map a retrieval chunk to its transcript.")
            end = start + len(doc.page_content)
            matched = [(i, segment) for left, right, i, segment in spans if left < end and right > start]
            if not matched:
                raise ValueError("Retrieval chunk has no source speech segments.")
            precision = "segment"
            if any(s.timing_precision == "chunk" for _, s in matched):
                precision = "chunk"
            elif any(s.timing_precision == "passage" for _, s in matched):
                precision = "passage"
            doc.metadata.update(
                start_seconds=min(s.start_seconds for _, s in matched),
                end_seconds=max(s.end_seconds for _, s in matched),
                timing_precision=precision,
                segment_ids=json.dumps([i for i, _ in matched]),
            )
    return docs


def build_vector_store(transcript, *, source_url: str = "") -> Chroma:
    # Each analysis gets its own collection. This also avoids stale untimed
    # passages from legacy collections being cited for a different video.
    collection_name = "meeting_" + uuid4().hex
    docs = build_documents(transcript, video_id=collection_name, source_url=source_url)
    return Chroma.from_documents(
        documents=docs, embedding=get_embeddings(),
        collection_name=collection_name, persist_directory=CHROMA_DIR,
    )


def load_vector_store(collection_name: str = COLLECTION_NAME) ->Chroma:
    embeddings = get_embeddings()
    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function= embeddings,
        persist_directory=CHROMA_DIR
    )

    return vector_store

def get_retriever(vector_store : Chroma, k :int = 4):
    return vector_store.as_retriever(
        search_type = 'similarity',
        search_kwargs = {"k":k}
    )


