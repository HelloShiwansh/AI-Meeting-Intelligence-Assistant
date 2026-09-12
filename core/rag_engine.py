import os
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from core.vector_store import build_vector_store, load_vector_store, get_retriever

def get_llm():
    return ChatMistralAI(
        model="mistral-small-latest",
        mistral_api_key=os.getenv("MISTRAL_API_KEY"),
        temperature=0.3,
    )

def format_docs(docs):
    return "\n\n".join([doc.page_content for doc in docs])


class ConversationalRAGChain:
    MAX_RECENT_MESSAGES = 4
    MAX_SUMMARY_LINES = 4

    def __init__(self, retriever, llm):
        self.retriever = retriever
        self.summary_chain = (
            ChatPromptTemplate.from_messages([
                (
                    "system",
                    """Summarize the earlier conversation for a meeting assistant.
Keep only facts, decisions, names, and references needed to understand future questions.
Do not invent information. Use no more than 4 short lines.""",
                ),
                ("human", "{conversation}"),
            ])
            | llm
            | StrOutputParser()
        )
        self.question_rewriter = (
            ChatPromptTemplate.from_messages([
                (
                    "system",
                    """Rewrite the user's latest question as a standalone question for retrieving information from a meeting transcript.
Use the conversation history to resolve references such as "it", "that decision", or "they".
If the question is already standalone, return it unchanged. Return only the rewritten question.""",
                ),
                MessagesPlaceholder("chat_history"),
                ("human", "{question}"),
            ])
            | llm
            | StrOutputParser()
        )
        self.answer_chain = (
            ChatPromptTemplate.from_messages([
                (
                    "system",
                    """You are an expert meeting assistant. Answer the user's question based ONLY on the meeting transcript context provided below.

If the answer is not found in the context, say:
"I could not find this information in the meeting transcript."

Always be concise and precise. If quoting someone, mention it clearly.

Context from meeting transcript:
{context}""",
                ),
                ("human", "{question}"),
            ])
            | llm
            | StrOutputParser()
        )

    @staticmethod
    def _as_messages(chat_history):
        messages = []
        for message in chat_history or []:
            if isinstance(message, (HumanMessage, AIMessage)):
                messages.append(message)
            elif message["role"] == "user":
                messages.append(HumanMessage(content=message["content"]))
            elif message["role"] == "assistant":
                messages.append(AIMessage(content=message["content"]))
        return messages

    def _compact_history(self, chat_history):
        if len(chat_history) <= self.MAX_RECENT_MESSAGES:
            return chat_history

        older_messages = chat_history[:-self.MAX_RECENT_MESSAGES]
        recent_messages = chat_history[-self.MAX_RECENT_MESSAGES:]
        conversation = "\n".join(
            f"{message.type}: {message.content}"
            for message in older_messages
        )
        summary = self.summary_chain.invoke({"conversation": conversation})
        summary = "\n".join(summary.splitlines()[:self.MAX_SUMMARY_LINES]).strip()

        return [
            SystemMessage(content=f"Summary of earlier conversation:\n{summary}"),
            *recent_messages,
        ]

    def invoke(self, input_data):
        if isinstance(input_data, str):
            input_data = {"question": input_data, "chat_history": []}

        question = input_data["question"]
        chat_history = self._compact_history(
            self._as_messages(input_data.get("chat_history", []))
        )
        search_question = self.question_rewriter.invoke({
            "question": question,
            "chat_history": chat_history,
        })
        docs = self.retriever.invoke(search_question)
        return self.answer_chain.invoke({
            "context": format_docs(docs),
            "question": search_question,
        })


def _build_chain(retriever, llm):
    return ConversationalRAGChain(retriever, llm)


def build_rag_chain(transcript: str):

    vector_store = build_vector_store(transcript)

    retriever = get_retriever(vector_store, k=4)

    llm = get_llm()
    return _build_chain(retriever, llm)


def load_rag_chain():
    vector_store = load_vector_store()
    retriever = get_retriever(vector_store)

    llm = get_llm()
    return _build_chain(retriever, llm)


def ask_question(rag_chain, question: str, chat_history=None) -> str:
    print(f"Question : {question}")
    answer = rag_chain.invoke({
        "question": question,
        "chat_history": chat_history or [],
    })
    print(f"answer :{answer}")
    return answer
