import os
from dotenv import load_dotenv

load_dotenv()

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

MINIMAX_MODEL = "MiniMax-M2.5"
MINIMAX_BASE_URL = "https://api.minimaxi.chat/v1"
EMBEDDING_MODEL = "text-embedding-ada-002"

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CHROMA_PERSIST_DIR = os.path.join(_BASE_DIR, "chroma_db")
CHROMA_COLLECTION_NAME = "orid_knowledge_base"  # legacy collection
KNOWLEDGE_DOCS_DIR = os.path.join(_BASE_DIR, "knowledge_docs")

# New data directories
DATA_DIR = os.path.join(_BASE_DIR, "data")
PROJECTS_DIR = os.path.join(DATA_DIR, "projects")
KB_REGISTRY_DIR = os.path.join(DATA_DIR, "kb_registry")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")

# Ensure data directories exist on import
for _d in (PROJECTS_DIR, KB_REGISTRY_DIR, REPORTS_DIR):
    os.makedirs(_d, exist_ok=True)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
RETRIEVAL_K = 4

LLM_TEMPERATURE = 0.1
LLM_MAX_TOKENS = 4096
