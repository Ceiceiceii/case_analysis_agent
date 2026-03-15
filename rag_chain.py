from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from config import MINIMAX_API_KEY, MINIMAX_BASE_URL, MINIMAX_MODEL, RETRIEVAL_K
from knowledge_base import get_vector_store
from prompts import CONTEXTUALIZE_Q_PROMPT, INITIAL_ANALYSIS_TEMPLATE, QA_PROMPT


def get_llm():
    return ChatOpenAI(
        model=MINIMAX_MODEL,
        api_key=MINIMAX_API_KEY,
        base_url=MINIMAX_BASE_URL,
        temperature=0.3,
        max_tokens=4096,
    )


def get_retriever():
    store = get_vector_store()
    return store.as_retriever(search_kwargs={"k": RETRIEVAL_K})


def _format_docs(docs) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


def convert_chat_history(messages: list[dict]) -> list:
    """Convert Streamlit message dicts to LangChain message objects."""
    history = []
    for msg in messages:
        if msg["role"] == "user":
            history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            history.append(AIMessage(content=msg["content"]))
    return history


def _contextualize_question(llm):
    """Build a chain that reformulates a follow-up question into a standalone one."""
    return CONTEXTUALIZE_Q_PROMPT | llm | StrOutputParser()


def build_rag_chain(llm, retriever):
    """Build a RAG chain using LCEL.

    The chain:
    1. Optionally reformulates the question using chat history
    2. Retrieves relevant ORID methodology chunks
    3. Passes context + chat history + question to Claude
    """
    contextualize_chain = _contextualize_question(llm)

    def get_standalone_question(input_dict):
        if input_dict.get("chat_history"):
            return contextualize_chain.invoke(input_dict)
        return input_dict["input"]

    def retrieve_and_format(input_dict):
        question = get_standalone_question(input_dict)
        docs = retriever.invoke(question)
        return _format_docs(docs)

    chain = (
        RunnablePassthrough.assign(context=retrieve_and_format)
        | QA_PROMPT
        | llm
        | StrOutputParser()
    )
    return chain


def generate_initial_report(document_text: str, rag_chain) -> str:
    """Generate the first ORID analysis of an uploaded document."""
    prompt = INITIAL_ANALYSIS_TEMPLATE.format(document_text=document_text)
    return rag_chain.invoke({
        "input": prompt,
        "chat_history": [],
    })


def ask_followup(question: str, chat_history: list[dict], rag_chain) -> str:
    """Ask a follow-up question using accumulated chat history."""
    lc_history = convert_chat_history(chat_history)
    return rag_chain.invoke({
        "input": question,
        "chat_history": lc_history,
    })
