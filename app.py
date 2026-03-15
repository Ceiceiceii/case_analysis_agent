"""Consulting Co-Pilot — Streamlit UI with LangGraph multi-agent orchestration."""

import json
import uuid

import streamlit as st

from config import MINIMAX_API_KEY, OPENAI_API_KEY
from graph.graph_builder import get_graph
from graph.routing import PHASE_ORDER, get_phase_display_name, get_phase_index
from state.project_store import (
    create_project,
    list_projects,
    load_project,
    save_project,
)
import knowledge_base as kb_module

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Consulting Co-Pilot",
    page_icon="🧠",
    layout="wide",
)

# ── Session state init ────────────────────────────────────────────────────────

def init_session():
    defaults = {
        "current_project_id": None,
        "graph_thread_id": str(uuid.uuid4()),
        "projects_list": [],
        "project_state": None,
        "pending_approval": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🧠 Consulting Co-Pilot")
    st.divider()

    # API key warnings
    if not MINIMAX_API_KEY:
        st.warning("MINIMAX_API_KEY not set in .env")
    if not OPENAI_API_KEY:
        st.warning("OPENAI_API_KEY not set in .env (needed for embeddings)")

    # ── Project management ────────────────────────────────────────────────────
    st.subheader("Projects")
    projects = list_projects()
    project_options = {f"{p['client_name']} — {p['project_type']}": p["project_id"] for p in projects}

    col1, col2 = st.columns([3, 1])
    with col1:
        selected_label = st.selectbox(
            "Select project",
            options=["— Select —"] + list(project_options.keys()),
            key="project_selector",
        )
    with col2:
        st.write("")
        st.write("")
        new_project_btn = st.button("New", use_container_width=True)

    if new_project_btn:
        st.session_state["show_new_project_form"] = True

    if st.session_state.get("show_new_project_form"):
        with st.form("new_project_form"):
            client_name = st.text_input("Client Name")
            project_type = st.selectbox(
                "Project Type",
                ["Strategy", "Operations", "Digital Transformation", "Market Entry",
                 "M&A Advisory", "Organizational Design", "Other"],
            )
            submitted = st.form_submit_button("Create Project")
            if submitted and client_name:
                new_state = create_project(client_name=client_name, project_type=project_type)
                st.session_state["current_project_id"] = new_state["project_id"]
                st.session_state["project_state"] = new_state
                st.session_state["graph_thread_id"] = str(uuid.uuid4())
                st.session_state["show_new_project_form"] = False
                st.success(f"Created project for {client_name}")
                st.rerun()

    # Load selected project
    if selected_label != "— Select —" and not st.session_state.get("show_new_project_form"):
        selected_id = project_options[selected_label]
        if selected_id != st.session_state["current_project_id"]:
            st.session_state["current_project_id"] = selected_id
            st.session_state["project_state"] = load_project(selected_id)
            st.session_state["graph_thread_id"] = str(uuid.uuid4())

    # ── Phase indicator ───────────────────────────────────────────────────────
    if st.session_state["project_state"]:
        ps = st.session_state["project_state"]
        current_phase = ps.get("phase", "intake")
        phase_idx = get_phase_index(current_phase)

        st.divider()
        st.subheader("Phase Progress")
        st.progress((phase_idx + 1) / len(PHASE_ORDER))
        for i, ph in enumerate(PHASE_ORDER):
            icon = "✅" if i < phase_idx else ("▶️" if i == phase_idx else "⬜")
            st.caption(f"{icon} {get_phase_display_name(ph)}")

        # ── KB Selector ───────────────────────────────────────────────────────
        st.divider()
        st.subheader("Knowledge Bases")
        all_kbs = kb_module.list_kbs()
        kb_map = {f"{kb['name']} ({kb['chunk_count']} chunks)": kb["kb_id"] for kb in all_kbs}

        kb_locked = ps.get("kb_locked", False)
        selected_kb_labels = st.multiselect(
            "Select KBs for this project",
            options=list(kb_map.keys()),
            default=[
                label for label, kid in kb_map.items()
                if kid in ps.get("selected_kb_ids", [])
            ],
            disabled=kb_locked,
        )
        selected_kb_ids = [kb_map[label] for label in selected_kb_labels]

        if selected_kb_ids != ps.get("selected_kb_ids", []):
            ps["selected_kb_ids"] = selected_kb_ids
            save_project(ps)
            st.session_state["project_state"] = ps

        lock_col1, lock_col2 = st.columns(2)
        with lock_col1:
            if not kb_locked and st.button("Lock KBs", use_container_width=True):
                ps["kb_locked"] = True
                save_project(ps)
                st.session_state["project_state"] = ps
                st.rerun()
        with lock_col2:
            if kb_locked:
                st.caption("🔒 KBs locked")

        # ── Report status badges ──────────────────────────────────────────────
        st.divider()
        st.subheader("Reports")
        for i in range(1, 4):
            report = ps.get(f"report_{i}")
            if report is None:
                st.caption(f"Report {i}: ⬜ Not generated")
            elif report.get("status") == "approved":
                st.caption(f"Report {i}: ✅ Approved (v{report.get('version', 1)})")
            elif report.get("status") == "rejected":
                st.caption(f"Report {i}: ❌ Rejected")
            else:
                st.caption(f"Report {i}: 📝 Draft (v{report.get('version', 1)})")

        # ── Phase advance (manual override) ──────────────────────────────────
        st.divider()
        if current_phase != "delivered":
            next_idx = min(phase_idx + 1, len(PHASE_ORDER) - 1)
            next_phase = PHASE_ORDER[next_idx]
            if st.button(f"Advance → {get_phase_display_name(next_phase)}", use_container_width=True):
                ps["phase"] = next_phase
                save_project(ps)
                st.session_state["project_state"] = ps
                st.rerun()

        # ── KB Upload ─────────────────────────────────────────────────────────
        st.divider()
        st.subheader("Upload to KB")
        target_kb_id = st.selectbox(
            "Target KB",
            options=[""] + [kb["kb_id"] for kb in all_kbs],
            format_func=lambda x: next((kb["name"] for kb in all_kbs if kb["kb_id"] == x), x or "— select —"),
        )
        uploaded_file = st.file_uploader(
            "Upload document",
            type=["txt", "pdf", "docx", "html", "csv"],
            disabled=kb_locked,
        )
        if uploaded_file and target_kb_id:
            if st.button("Ingest Document"):
                with st.spinner("Ingesting..."):
                    chunks = kb_module.ingest_into_kb(
                        target_kb_id,
                        uploaded_file.read(),
                        uploaded_file.name,
                    )
                st.success(f"Ingested {chunks} chunks into KB.")
                st.rerun()


# ── Main area ─────────────────────────────────────────────────────────────────

if not st.session_state["current_project_id"] or not st.session_state["project_state"]:
    st.title("Consulting Co-Pilot")
    st.info("Select an existing project from the sidebar or create a new one to get started.")
    st.stop()

ps = st.session_state["project_state"]
client_name = ps.get("client_name", "")
project_type = ps.get("project_type", "")
current_phase = ps.get("phase", "intake")

st.title(f"🧠 {client_name} — {project_type}")
st.caption(f"Phase: **{get_phase_display_name(current_phase)}** | Project ID: `{ps['project_id']}`")

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_chat, tab_reports, tab_kbs = st.tabs(["💬 Chat", "📄 Reports", "📚 Knowledge Bases"])

# ── Chat tab ──────────────────────────────────────────────────────────────────

with tab_chat:
    # Display conversation history
    conversation = ps.get("conversation_history", [])
    for msg in conversation:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        agent = msg.get("agent", "")

        if role == "user":
            with st.chat_message("user"):
                st.write(content)
        else:
            with st.chat_message("assistant"):
                if agent:
                    st.caption(f"_{agent}_")
                st.write(content)

    # Pending approval widget
    pending = ps.get("pending_approval")
    if pending and pending.get("type") == "enrichment":
        st.warning("**Pending KB Enrichment Approval**")
        proposed = pending.get("proposed_sources", [])
        for src in proposed:
            col_a, col_b = st.columns([4, 1])
            with col_a:
                st.write(f"**{src.get('title', '')}** [{src.get('confidence', '')}]")
                st.caption(src.get("url", ""))
                st.write(src.get("content", "")[:200])
            with col_b:
                src["_selected"] = st.checkbox("Approve", key=f"approve_{src.get('url', '')}")

        col_ok, col_cancel = st.columns(2)
        with col_ok:
            if st.button("Approve Selected"):
                approved_urls = [s["url"] for s in proposed if s.get("_selected")]
                # Ingest approved sources
                kb_id = pending.get("kb_id", "")
                if kb_id and approved_urls:
                    for src in proposed:
                        if src["url"] in approved_urls and src.get("content"):
                            kb_module.ingest_into_kb(
                                kb_id,
                                src["content"].encode("utf-8"),
                                f"web_{src['title'][:40]}.txt",
                                source_url=src["url"],
                            )
                    ps["pending_approval"] = None
                    save_project(ps)
                    st.session_state["project_state"] = ps
                    st.success(f"Approved and ingested {len(approved_urls)} sources.")
                    st.rerun()
        with col_cancel:
            if st.button("Reject All"):
                ps["pending_approval"] = None
                save_project(ps)
                st.session_state["project_state"] = ps
                st.rerun()

    # Draft report approval
    for i in range(1, 4):
        report = ps.get(f"report_{i}")
        if report and report.get("status") == "draft":
            st.info(f"**Report {i}** is ready for review. Approve or reject below.")
            with st.expander(f"Preview Report {i}", expanded=False):
                st.markdown(report.get("content", ""))
            col_approve, col_reject = st.columns(2)
            with col_approve:
                if st.button(f"✅ Approve Report {i}", key=f"approve_r{i}"):
                    from datetime import datetime
                    report["status"] = "approved"
                    report["approved_at"] = datetime.utcnow().isoformat()
                    ps[f"report_{i}"] = report
                    save_project(ps)
                    st.session_state["project_state"] = ps
                    st.success(f"Report {i} approved!")
                    st.rerun()
            with col_reject:
                if st.button(f"❌ Reject Report {i}", key=f"reject_r{i}"):
                    report["status"] = "rejected"
                    ps[f"report_{i}"] = report
                    save_project(ps)
                    st.session_state["project_state"] = ps
                    st.rerun()

    # Chat input
    user_input = st.chat_input("Message the consulting co-pilot...")
    if user_input:
        # Add user message to conversation
        ps["conversation_history"] = ps.get("conversation_history", []) + [{
            "role": "user",
            "content": user_input,
            "agent": "user",
        }]

        # Determine target node from user input
        from graph.routing import resolve_next_node
        target_node = resolve_next_node(user_input, current_phase)
        ps["next_node"] = target_node or "orchestrator"

        save_project(ps)
        st.session_state["project_state"] = ps

        # Run graph
        with st.spinner("Thinking..."):
            try:
                graph = get_graph()
                config = {"configurable": {"thread_id": st.session_state["graph_thread_id"]}}

                # Build state for this turn
                turn_state = {
                    "project_id": ps["project_id"],
                    "client_name": ps["client_name"],
                    "project_type": ps["project_type"],
                    "phase": ps["phase"],
                    "selected_kb_ids": ps.get("selected_kb_ids", []),
                    "kb_locked": ps.get("kb_locked", False),
                    "conversation_history": [{
                        "role": "user",
                        "content": user_input,
                        "agent": "user",
                    }],
                    "discovery_answers": ps.get("discovery_answers", {}),
                    "discovery_questions": ps.get("discovery_questions", []),
                    "report_1": ps.get("report_1"),
                    "report_2": ps.get("report_2"),
                    "report_3": ps.get("report_3"),
                    "current_report_version": ps.get("current_report_version", 0),
                    "source_citations": [],
                    "kb_enrichment_log": [],
                    "next_node": ps.get("next_node", "orchestrator"),
                    "agent_message": "",
                    "error": None,
                    "pending_approval": ps.get("pending_approval"),
                }

                result = graph.invoke(turn_state, config=config)

                # Merge results back into project state
                for key in ["report_1", "report_2", "report_3", "discovery_answers",
                            "pending_approval", "phase", "kb_locked"]:
                    if key in result and result[key] is not None:
                        ps[key] = result[key]

                # Append new conversation entries
                new_conv = result.get("conversation_history", [])
                existing_ids = {(m["role"], m["content"]) for m in ps.get("conversation_history", [])}
                for msg in new_conv:
                    if msg.get("role") == "assistant":
                        key = (msg["role"], msg["content"])
                        if key not in existing_ids:
                            ps["conversation_history"] = ps.get("conversation_history", []) + [msg]
                            existing_ids.add(key)

                save_project(ps)
                st.session_state["project_state"] = ps

            except Exception as e:
                st.error(f"Graph error: {e}")

        st.rerun()


# ── Reports tab ───────────────────────────────────────────────────────────────

with tab_reports:
    st.subheader("Generated Reports")

    report_tabs = st.tabs(["Report 1 — Background", "Report 2 — Analysis", "Report 3 — Recommendations"])

    for i, rtab in enumerate(report_tabs, 1):
        with rtab:
            report = ps.get(f"report_{i}")
            if report is None:
                st.info(f"Report {i} has not been generated yet.")
                continue

            st.write(f"**Version:** {report.get('version', 1)} | **Status:** {report.get('status', 'draft').upper()}")
            st.write(f"Generated: {report.get('generated_at', 'N/A')}")
            if report.get("approved_at"):
                st.write(f"Approved: {report['approved_at']}")

            with st.expander("Report Content", expanded=True):
                st.markdown(report.get("content", ""))

            # Export buttons
            col_md, col_docx = st.columns(2)
            with col_md:
                from export.report_exporter import export_to_markdown
                md_content = export_to_markdown(report)
                st.download_button(
                    label="Download Markdown",
                    data=md_content,
                    file_name=f"{ps['project_id']}_report_{i}_v{report.get('version', 1)}.md",
                    mime="text/markdown",
                )
            with col_docx:
                try:
                    from export.report_exporter import export_to_docx
                    docx_bytes = export_to_docx(report)
                    st.download_button(
                        label="Download DOCX",
                        data=docx_bytes,
                        file_name=f"{ps['project_id']}_report_{i}_v{report.get('version', 1)}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                except Exception as e:
                    st.caption(f"DOCX export unavailable: {e}")


# ── KBs tab ───────────────────────────────────────────────────────────────────

with tab_kbs:
    st.subheader("Knowledge Base Management")

    all_kbs = kb_module.list_kbs()

    # Create new KB
    with st.expander("Create New KB"):
        with st.form("create_kb_form"):
            kb_name = st.text_input("KB Name")
            kb_desc = st.text_area("Description", height=80)
            if st.form_submit_button("Create KB"):
                if kb_name:
                    meta = kb_module.create_kb(name=kb_name, description=kb_desc)
                    st.success(f"Created KB: {meta['name']} (ID: {meta['kb_id']})")
                    st.rerun()

    if not all_kbs:
        st.info("No knowledge bases yet. Create one above.")
    else:
        for kb in all_kbs:
            with st.expander(f"📚 {kb['name']} — {kb.get('chunk_count', 0)} chunks"):
                st.write(f"**ID:** `{kb['kb_id']}`")
                st.write(f"**Description:** {kb.get('description', '—')}")
                st.write(f"**Created:** {kb.get('created_at', '—')}")
                keywords = kb.get("keywords", [])
                st.write(f"**Keywords:** {', '.join(keywords) if keywords else '—'}")

                # Set keywords
                new_keywords = st.text_input(
                    "Update keywords (comma-separated)",
                    value=", ".join(keywords),
                    key=f"kw_{kb['kb_id']}",
                )
                if st.button("Save Keywords", key=f"save_kw_{kb['kb_id']}"):
                    kw_list = [k.strip() for k in new_keywords.split(",") if k.strip()]
                    kb_module.set_kb_keywords(kb["kb_id"], kw_list)
                    st.success("Keywords updated.")
                    st.rerun()

                # Sources
                sources = kb.get("sources", [])
                if sources:
                    st.write(f"**Sources ({len(sources)}):**")
                    for src in sources[-5:]:
                        st.caption(f"• {src.get('filename', src.get('url', '—'))} @ {src.get('ingested_at', '')[:10]}")
