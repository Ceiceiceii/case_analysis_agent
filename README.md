# Case Analysis Agent

A multi-agent consulting co-pilot built with LangGraph that guides users through structured case analysis using the ORID (Objective, Reflective, Interpretive, Decisional) framework.

## Architecture

Hub-and-spoke multi-agent graph powered by LangGraph:

- **Orchestrator** — Routes conversations and enforces phase gates
- **KB Manager** — Manages knowledge bases (create, ingest, search, enrich)
- **Analyst** — Runs discovery questionnaires and structured analysis
- **Brainstorm** — Generates creative solutions grounded in KB context
- **Report Generator** — Produces phased reports with version tracking

## 8-Phase Workflow

`intake → discovery → report_1 → analysis → report_2 → brainstorm → report_3 → delivered`

Each phase builds on the previous, with report approval gates between stages.

## Tech Stack

- **LLM**: MiniMax M2.5 via OpenAI-compatible API
- **Embeddings**: OpenAI `text-embedding-ada-002`
- **Vector Store**: ChromaDB (persistent, multi-collection)
- **Framework**: LangGraph + LangChain
- **Web Search**: Tavily (primary) / DuckDuckGo (fallback)
- **UI**: Streamlit

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```
   MINIMAX_API_KEY=...
   OPENAI_API_KEY=...
   TAVILY_API_KEY=...  # optional
   ```

3. Run the app:
   ```bash
   streamlit run app.py
   ```

## Project Structure

```
├── agents/          # Agent nodes (orchestrator, analyst, kb_manager, brainstorm, report_generator)
├── graph/           # LangGraph builder and routing logic
├── state/           # Project state schema and JSON persistence
├── tools/           # Tool functions (KB, discovery, analysis, report, search)
├── export/          # Report export (Markdown, DOCX)
├── data/            # Projects, KB registry, reports
├── knowledge_docs/  # Source documents
├── app.py           # Streamlit UI
├── config.py        # Environment config
├── knowledge_base.py# ChromaDB multi-KB management
├── prompts.py       # System prompts for each agent
└── document_parser.py # PDF, HTML, CSV parsing
```
